"""Analytics / Dashboard API endpoints."""
import logging
from typing import Any, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import dependencies
from app.api.dependencies import RoleChecker
from app.models.post import Post
from app.schemas.dashboard import (
    DashboardPostItem,
    DashboardPostListResponse,
    DashboardStats,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Admin-only guard
allow_admin = RoleChecker(["admin"])


# ── Business Logic (extracted for testability) ─────────────────────

async def get_dashboard_stats(db: AsyncSession) -> dict:
    """Compute aggregate stats from the posts table."""
    total_q = select(func.count(Post.id)).where(Post.deleted_at.is_(None))
    published_q = total_q.where(Post.status == "published")
    draft_q = total_q.where(Post.status == "draft")
    views_q = select(func.coalesce(func.sum(Post.view_count), 0)).where(
        Post.deleted_at.is_(None)
    )

    total = (await db.execute(total_q)).scalar() or 0
    published = (await db.execute(published_q)).scalar() or 0
    draft = (await db.execute(draft_q)).scalar() or 0
    total_views = (await db.execute(views_q)).scalar() or 0

    return {
        "total_articles": total,
        "published_articles": published,
        "draft_articles": draft,
        "total_views": total_views,
        "views_trend": None,  # Requires history tracking table
    }


async def get_dashboard_posts(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 20,
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    sort: Optional[str] = None,
) -> Tuple[List[Post], int]:
    """Fetch paginated posts for admin dashboard table."""
    query = (
        select(Post)
        .where(Post.deleted_at.is_(None))
        .options(
            selectinload(Post.author),
            selectinload(Post.category),
        )
    )

    if status_filter:
        query = query.where(Post.status == status_filter)
    if category:
        from app.models.category import Category
        query = query.join(Post.category).where(Category.slug == category)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Sort
    if sort == "views":
        query = query.order_by(Post.view_count.desc())
    elif sort == "title":
        query = query.order_by(Post.title.asc())
    else:
        query = query.order_by(Post.created_at.desc())

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().unique().all()), total


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(
    db: AsyncSession = Depends(dependencies.get_db),
    current_user=Depends(allow_admin),
) -> Any:
    """Retrieve summary statistics for the admin dashboard."""
    return await get_dashboard_stats(db)


@router.get("/dashboard/posts", response_model=DashboardPostListResponse)
async def dashboard_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    sort: Optional[str] = None,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user=Depends(allow_admin),
) -> Any:
    """Retrieve admin post table with extended details."""
    posts, total = await get_dashboard_posts(
        db,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
        category=category,
        sort=sort,
    )
    items = [
        DashboardPostItem(
            id=p.id,
            title=p.title,
            slug=p.slug,
            status=p.status,
            category=p.category,
            views=p.view_count,
            author=p.author,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in posts
    ]
    return DashboardPostListResponse(total=total, items=items)
