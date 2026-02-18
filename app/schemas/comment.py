from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.post import AuthorBrief


# ── Base / Create / Update ──────────────────────────────────────────

class CommentBase(BaseModel):
    content: Optional[str] = None


class CommentCreate(BaseModel):
    """Client-facing create schema. post_id and user_id injected server-side."""
    content: str = Field(..., min_length=1, max_length=5000)


class CommentUpdate(CommentBase):
    pass


# ── DB / Response schemas ───────────────────────────────────────────

class CommentInDBBase(CommentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    is_approved: bool
    post_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class Comment(CommentInDBBase):
    pass


class CommentInDB(CommentInDBBase):
    pass


# ── API response schemas ───────────────────────────────────────────

class CommentListItem(BaseModel):
    """Comment as displayed in list responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    user: Optional[AuthorBrief] = None
    created_at: datetime


class CommentListResponse(BaseModel):
    """Paginated comment list wrapper."""
    total: int
    items: List[CommentListItem]
