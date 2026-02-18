"""Dashboard / Analytics schemas."""
from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardStats(BaseModel):
    """Summary statistics for the admin dashboard."""
    total_articles: int
    published_articles: int
    draft_articles: int
    total_views: int
    views_trend: Optional[str] = None


# ── Nested schemas for dashboard post list ──────────────────────────

class DashboardCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str


class DashboardAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    full_name: Optional[str] = None


class DashboardPostItem(BaseModel):
    """Extended post row for the admin post table."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    status: str
    category: Optional[DashboardCategory] = None
    views: int = 0
    author: Optional[DashboardAuthor] = None
    created_at: datetime
    updated_at: datetime


class DashboardPostListResponse(BaseModel):
    """Paginated dashboard post list wrapper."""
    total: int
    items: List[DashboardPostItem]
