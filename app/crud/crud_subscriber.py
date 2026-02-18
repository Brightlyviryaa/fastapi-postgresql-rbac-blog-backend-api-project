"""CRUD operations for newsletter subscribers."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.subscriber import Subscriber
from app.schemas.subscriber import SubscriberCreate, SubscriberUpdate


class CRUDSubscriber(CRUDBase[Subscriber, SubscriberCreate, SubscriberUpdate]):

    async def get_by_email(
        self, db: AsyncSession, *, email: str
    ) -> Optional[Subscriber]:
        """Fetch a subscriber by email address."""
        result = await db.execute(
            select(Subscriber).where(Subscriber.email == email)
        )
        return result.scalars().first()

    async def reactivate(
        self, db: AsyncSession, *, db_obj: Subscriber
    ) -> Subscriber:
        """Re-activate a previously deactivated subscriber."""
        db_obj.is_active = True
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def deactivate(
        self, db: AsyncSession, *, db_obj: Subscriber
    ) -> Subscriber:
        """Soft-deactivate a subscriber (unsubscribe)."""
        db_obj.is_active = False
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


subscriber = CRUDSubscriber(Subscriber)
