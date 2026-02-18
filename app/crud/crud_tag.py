from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.tag import Tag
from app.schemas.tag import TagCreate


class CRUDTag(CRUDBase[Tag, TagCreate, TagCreate]):

    async def get_multi_filtered(
        self,
        db: AsyncSession,
        *,
        q: Optional[str] = None,
    ) -> List[Tag]:
        """Return tags, optionally filtered by search term."""
        query = select(Tag)
        if q:
            query = query.where(Tag.name.ilike(f"%{q}%"))
        query = query.order_by(Tag.name)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_slug(self, db: AsyncSession, *, slug: str):
        result = await db.execute(
            select(Tag).where(Tag.slug == slug)
        )
        return result.scalars().first()


tag = CRUDTag(Tag)
