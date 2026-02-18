from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.category import Category
from app.schemas.tag import Tag


# ── Nested helper schemas (for API responses) ──────────────────────

class AuthorBrief(BaseModel):
    """Minimal author representation embedded in post responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: Optional[str] = None


class AuthorDetail(AuthorBrief):
    """Extended author with avatar, used in post detail."""
    avatar_url: Optional[str] = None


class RelatedPost(BaseModel):
    """Minimal post card used in the related-posts section."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    thumbnail_url: Optional[str] = None


# ── Base / Create / Update ──────────────────────────────────────────

class PostBase(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = "draft"
    visibility: Optional[str] = "public"
    thumbnail_url: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical_url: Optional[str] = None
    pdf_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    category_id: Optional[int] = None


class PostCreate(PostBase):
    """Schema for creating a new post. `author_id` is injected server-side."""
    title: str = Field(..., min_length=1, max_length=500)
    slug: str = Field(..., min_length=1, max_length=500)
    content: Optional[str] = None
    pdf_url: Optional[str] = None
    tag_ids: Optional[List[int]] = None

    @model_validator(mode="after")
    def check_content_or_pdf(self) -> "PostCreate":
        if not self.content and not self.pdf_url:
            raise ValueError("Either content or pdf_url must be provided")
        return self


class PostUpdate(PostBase):
    """Schema for updating a post. All fields optional."""
    tag_ids: Optional[List[int]] = None


# ── DB / Response schemas ───────────────────────────────────────────

class PostInDBBase(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    content: Optional[str] = None
    pdf_url: Optional[str] = None
    author_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class Post(PostInDBBase):
    """Full post (internal use — prefer PostListItem / PostDetail for API)."""
    pass


class PostInDB(PostInDBBase):
    pass


# ── API response schemas ───────────────────────────────────────────

class PostListItem(BaseModel):
    """Summary post card returned in list endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    status: str
    view_count: int = 0
    reading_time: Optional[int] = None
    category: Optional[Category] = None
    author: Optional[AuthorBrief] = None
    created_at: datetime
    updated_at: datetime


class PostListResponse(BaseModel):
    """Paginated list wrapper."""
    total: int
    items: List[PostListItem]


class PostDetail(BaseModel):
    """Full post detail with all relations."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    content: Optional[str] = None
    abstract: Optional[str] = None
    pdf_url: Optional[str] = None
    status: str
    view_count: int = 0
    reading_time: Optional[int] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    thumbnail_url: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical_url: Optional[str] = None
    category: Optional[Category] = None
    tags: List[Tag] = []
    author: Optional[AuthorBrief] = None
    related_posts: List[RelatedPost] = []
    created_at: datetime
    updated_at: datetime
