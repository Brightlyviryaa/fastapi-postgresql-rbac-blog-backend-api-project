from typing import List, Optional, Tuple

import bleach
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.comment import Comment
from app.models.post import Post
from app.schemas.comment import CommentCreate, CommentUpdate

# Allowed tags for comment content (very restrictive).
COMMENT_ALLOWED_TAGS: list[str] = []  # No HTML allowed in comments.

MAX_COMMENT_LENGTH = 5000


def sanitize_comment(raw: str) -> str:
    """Strip ALL HTML from comment content."""
    return bleach.clean(raw, tags=COMMENT_ALLOWED_TAGS, strip=True)


class CRUDComment(CRUDBase[Comment, CommentCreate, CommentUpdate]):

    async def get_by_post_slug(
        self,
        db: AsyncSession,
        *,
        post_slug: str,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Comment], int]:
        """Return approved comments for a given post slug (paginated)."""
        post_subq = select(Post.id).where(
            Post.slug == post_slug, Post.deleted_at.is_(None)
        ).scalar_subquery()

        base = select(Comment).where(
            Comment.post_id == post_subq,
            Comment.is_approved.is_(True),
        ).options(selectinload(Comment.user))

        count_q = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        query = base.order_by(Comment.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def create_comment(
        self,
        db: AsyncSession,
        *,
        content: str,
        post_id: int,
        user_id: int,
    ) -> Comment:
        """Create a comment with sanitized content, pending approval."""
        clean_content = sanitize_comment(content)
        if len(clean_content) > MAX_COMMENT_LENGTH:
            raise ValueError("Comment exceeds maximum allowed length")

        db_obj = Comment(
            content=clean_content,
            post_id=post_id,
            user_id=user_id,
            is_approved=False,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj, attribute_names=["user"])
        return db_obj

    async def approve(self, db: AsyncSession, *, db_obj: Comment) -> Comment:
        """Approve a comment for public display."""
        db_obj.is_approved = True
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: int) -> Optional[Comment]:
        """Hard delete a comment."""
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj


comment = CRUDComment(Comment)
