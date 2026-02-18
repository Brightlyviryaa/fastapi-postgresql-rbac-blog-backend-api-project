"""Newsletter Subscribers API endpoints."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.api import dependencies

logger = logging.getLogger(__name__)

router = APIRouter()


class SubscribeRequest(BaseModel):
    """Request body for subscribing."""
    email: EmailStr = Field(..., max_length=254)


class SubscribeResponse(BaseModel):
    """Simple message response."""
    message: str


# ── Subscribe ───────────────────────────────────────────────────────

@router.post("/subscribers", response_model=SubscribeResponse)
async def subscribe(
    body: SubscribeRequest,
    db: AsyncSession = Depends(dependencies.get_db),
) -> Any:
    """Subscribe an email to the newsletter. Idempotent."""
    existing = await crud.subscriber.get_by_email(db, email=body.email)

    if existing:
        if existing.is_active:
            return SubscribeResponse(message="Already subscribed.")
        # Reactivate a previously unsubscribed email.
        await crud.subscriber.reactivate(db, db_obj=existing)
        return SubscribeResponse(message="Successfully subscribed.")

    from app.schemas.subscriber import SubscriberCreate
    await crud.subscriber.create(db, obj_in=SubscriberCreate(email=body.email))
    return SubscribeResponse(message="Successfully subscribed.")


# ── Unsubscribe ─────────────────────────────────────────────────────

@router.delete("/subscribers/{email}", response_model=SubscribeResponse)
async def unsubscribe(
    email: str,
    db: AsyncSession = Depends(dependencies.get_db),
) -> Any:
    """Unsubscribe an email from the newsletter."""
    existing = await crud.subscriber.get_by_email(db, email=email)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscriber not found",
        )
    await crud.subscriber.deactivate(db, db_obj=existing)
    return SubscribeResponse(message="Successfully unsubscribed.")
