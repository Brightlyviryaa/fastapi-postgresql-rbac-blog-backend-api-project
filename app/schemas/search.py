"""Search API schemas."""
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SearchCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    slug: str


class SearchAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    full_name: Optional[str] = None


class SearchResultItem(BaseModel):
    """A single search result entry."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    highlight: Optional[str] = None
    category: Optional[SearchCategory] = None
    author: Optional[SearchAuthor] = None
    published_at: Optional[datetime] = None
    relevance_score: Optional[float] = None


class SearchResponse(BaseModel):
    """Paginated search results wrapper."""
    total: int
    items: List[SearchResultItem]
