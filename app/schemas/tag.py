from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# Shared properties
class TagBase(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None


# Properties to receive on creation
class TagCreate(TagBase):
    name: str
    slug: str


# Properties to return to client
class Tag(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
