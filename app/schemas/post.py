from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator

# Shared properties
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

# Properties to receive on Post creation
    title: str
    slug: str
    content: Optional[str] = None
    pdf_url: Optional[str] = None
    author_id: int

    @model_validator(mode='after')
    def check_content_or_pdf(self) -> 'PostCreate':
        if not self.content and not self.pdf_url:
            raise ValueError('Either content or pdf_url must be provided')
        return self

# Properties to receive on Post update
class PostUpdate(PostBase):
    pass

# Properties shared by models stored in DB
class PostInDBBase(PostBase):
    id: int
    title: str
    slug: str
    content: Optional[str] = None
    pdf_url: Optional[str] = None
    author_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Properties to return to client
class Post(PostInDBBase):
    pass

# Properties stored in DB
class PostInDB(PostInDBBase):
    pass
