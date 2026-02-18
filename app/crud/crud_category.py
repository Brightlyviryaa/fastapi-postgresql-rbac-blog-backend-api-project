from typing import List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.category import Category
from app.models.post import Post
from app.schemas.category import CategoryCreate


class CRUDCategory(CRUDBase[Category, CategoryCreate, CategoryCreate]):

    async def get_multi_with_count(self, db: AsyncSession) -> List[dict]:
        """Return all categories with their associated post count."""
        post_count = (
            select(func.count(Post.id))
            .where(Post.category_id == Category.id, Post.deleted_at.is_(None))
            .correlate(Category)
            .scalar_subquery()
        )

        query = select(
            Category,
            post_count.label("count"),
        ).order_by(Category.name)

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "id": row[0].id,
                "name": row[0].name,
                "slug": row[0].slug,
                "count": row[1] or 0,
            }
            for row in rows
        ]

    async def get_by_slug(self, db: AsyncSession, *, slug: str):
        result = await db.execute(
            select(Category).where(Category.slug == slug)
        )
        return result.scalars().first()


category = CRUDCategory(Category)
