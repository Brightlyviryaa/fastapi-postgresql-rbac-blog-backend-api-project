from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# Shared properties
class CategoryBase(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None


# Properties to receive on creation
class CategoryCreate(CategoryBase):
    name: str
    slug: str


# Properties to return to client (includes post count)
class Category(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class CategoryWithCount(Category):
    """Category with the number of associated posts."""
    count: int = 0
