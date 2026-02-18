"""Analytics / Dashboard API endpoints."""
import json
import logging
from typing import Any, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import dependencies
from app.api.dependencies import RoleChecker
from app.core.cache import cache_get, cache_invalidate, cache_set
from app.core.config import settings
from app.core.redis import get_redis
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
    redis: Redis = Depends(get_redis),
    current_user=Depends(allow_admin),
) -> Any:
    """Retrieve summary statistics for the admin dashboard."""
    # Cache-aside: check cache first
    cached = await cache_get(redis, "dashboard_stats")
    if cached:
        return DashboardStats(**json.loads(cached))

    data = await get_dashboard_stats(db)
    response = DashboardStats(**data)

    await cache_set(
        redis,
        "dashboard_stats",
        response.model_dump_json(),
        ttl=settings.CACHE_TTL_DASHBOARD_STATS,
    )
    return response


@router.get("/dashboard/posts", response_model=DashboardPostListResponse)
async def dashboard_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    sort: Optional[str] = None,
    db: AsyncSession = Depends(dependencies.get_db),
    redis: Redis = Depends(get_redis),
    current_user=Depends(allow_admin),
) -> Any:
    """Retrieve admin post table with extended details."""
    cache_params = dict(
        skip=skip, limit=limit,
        status=status_filter or "", category=category or "", sort=sort or "",
    )

    cached = await cache_get(redis, "dashboard_posts", **cache_params)
    if cached:
        return DashboardPostListResponse(**json.loads(cached))

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
    response = DashboardPostListResponse(total=total, items=items)

    await cache_set(
        redis,
        "dashboard_posts",
        response.model_dump_json(),
        ttl=settings.CACHE_TTL_DASHBOARD_POSTS,
        **cache_params,
    )
    return response
