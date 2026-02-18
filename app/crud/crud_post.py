from typing import Any, Dict, List, Optional, Tuple, Union

import bleach
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.category import Category
from app.models.post import Post
from app.models.tag import Tag
from app.schemas.post import PostCreate, PostUpdate

# Allowed HTML tags/attrs for post content sanitization.
ALLOWED_TAGS = [
    "p", "br", "b", "i", "u", "em", "strong", "a",
    "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "code", "pre", "img", "table", "thead",
    "tbody", "tr", "th", "td", "figure", "figcaption",
    "span", "div", "sub", "sup", "hr",
]
ALLOWED_ATTRS = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
    "span": ["class"],
    "div": ["class"],
    "code": ["class"],
    "pre": ["class"],
}

# Maximum allowed content length (characters).
MAX_CONTENT_LENGTH = 200_000


def sanitize_html(raw: Optional[str]) -> Optional[str]:
    """Strip dangerous HTML tags/attributes from content."""
    if raw is None:
        return None
    return bleach.clean(raw, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


class CRUDPost(CRUDBase[Post, PostCreate, PostUpdate]):

    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 10,
        status: Optional[str] = None,
        category_slug: Optional[str] = None,
        tag_slug: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Post], int]:
        """Return paginated posts matching filters + total count."""
        query = (
            select(Post)
            .where(Post.deleted_at.is_(None))
            .options(
                selectinload(Post.author),
                selectinload(Post.category),
            )
        )

        if status:
            query = query.where(Post.status == status)
        if category_slug:
            query = query.join(Post.category).where(Category.slug == category_slug)
        if tag_slug:
            query = query.join(Post.tags).where(Tag.slug == tag_slug)
        if search:
            query = query.where(Post.title.ilike(f"%{search}%"))

        # Total count (before pagination).
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        # Paginated results.
        query = query.order_by(Post.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().unique().all()), total

    async def get_by_slug(self, db: AsyncSession, *, slug: str) -> Optional[Post]:
        """Fetch a single post by slug, eager-loading relations."""
        query = (
            select(Post)
            .where(Post.slug == slug, Post.deleted_at.is_(None))
            .options(
                selectinload(Post.author),
                selectinload(Post.category),
                selectinload(Post.tags),
                selectinload(Post.comments),
            )
        )
        result = await db.execute(query)
        return result.scalars().first()

    async def create_with_tags(
        self,
        db: AsyncSession,
        *,
        obj_in: PostCreate,
        author_id: int,
    ) -> Post:
        """Create a post, sanitize HTML content, and attach tags."""
        content = sanitize_html(obj_in.content)
        if content and len(content) > MAX_CONTENT_LENGTH:
            raise ValueError("Content exceeds maximum allowed length")

        db_obj = Post(
            title=obj_in.title,
            slug=obj_in.slug,
            content=content,
            status=obj_in.status or "draft",
            visibility=obj_in.visibility or "public",
            thumbnail_url=obj_in.thumbnail_url,
            meta_title=obj_in.meta_title,
            meta_description=obj_in.meta_description,
            canonical_url=obj_in.canonical_url,
            pdf_url=obj_in.pdf_url,
            scheduled_at=obj_in.scheduled_at,
            category_id=obj_in.category_id,
            author_id=author_id,
        )

        # Attach tags (M2M).
        if obj_in.tag_ids:
            tag_result = await db.execute(
                select(Tag).where(Tag.id.in_(obj_in.tag_ids))
            )
            db_obj.tags = list(tag_result.scalars().all())

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj, attribute_names=["author", "category", "tags"])
        return db_obj

    async def update_with_tags(
        self,
        db: AsyncSession,
        *,
        db_obj: Post,
        obj_in: Union[PostUpdate, Dict[str, Any]],
    ) -> Post:
        """Update a post, sanitize content, and sync tags."""
        if isinstance(obj_in, dict):
            update_data = obj_in
            tag_ids = update_data.pop("tag_ids", None)
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
            tag_ids = update_data.pop("tag_ids", None)

        # Sanitize content if being updated.
        if "content" in update_data and update_data["content"] is not None:
            update_data["content"] = sanitize_html(update_data["content"])
            if len(update_data["content"]) > MAX_CONTENT_LENGTH:
                raise ValueError("Content exceeds maximum allowed length")

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Sync tags.
        if tag_ids is not None:
            tag_result = await db.execute(
                select(Tag).where(Tag.id.in_(tag_ids))
            )
            db_obj.tags = list(tag_result.scalars().all())

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj, attribute_names=["author", "category", "tags"])
        return db_obj

    async def soft_delete(self, db: AsyncSession, *, db_obj: Post) -> Post:
        """Soft-delete a post by setting deleted_at."""
        from datetime import datetime, timezone

        db_obj.deleted_at = datetime.now(timezone.utc)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


post = CRUDPost(Post)
