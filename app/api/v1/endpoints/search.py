"""Search API endpoint."""
import json
import logging
from typing import Any, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import dependencies
from app.core.cache import cache_get, cache_set
from app.core.config import settings
from app.core.redis import get_redis
from app.models.category import Category
from app.models.post import Post
from app.schemas.search import SearchResponse, SearchResultItem

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Business Logic (extracted for testability) ─────────────────────

async def search_posts(
    db: AsyncSession,
    *,
    q: str,
    category_filter: Optional[str] = None,
    sort: str = "relevance",
    skip: int = 0,
    limit: int = 10,
) -> Tuple[List[Post], int]:
    """Keyword search on published posts (title + content ILIKE).

    Note: Semantic/vector search requires an external embedding pipeline
    and is not yet implemented. This fallback uses keyword matching.
    """
    query = (
        select(Post)
        .where(Post.deleted_at.is_(None), Post.status == "published")
        .options(
            selectinload(Post.author),
            selectinload(Post.category),
        )
    )

    # Keyword search (title OR content)
    search_pattern = f"%{q}%"
    query = query.where(
        (Post.title.ilike(search_pattern)) | (Post.content.ilike(search_pattern))
    )

    # Category filter
    if category_filter and category_filter != "all":
        query = query.join(Post.category).where(Category.slug == category_filter)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Sort
    if sort == "date":
        query = query.order_by(Post.created_at.desc())
    else:
        # Relevance: title matches weighted higher (title match first, then date)
        query = query.order_by(Post.title.ilike(search_pattern).desc(), Post.created_at.desc())

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().unique().all()), total


def _build_excerpt(content: Optional[str], max_length: int = 200) -> Optional[str]:
    """Extract a plain-text excerpt from HTML content."""
    if not content:
        return None
    import re
    text = re.sub(r"<[^>]+>", "", content)
    return text[:max_length] + "..." if len(text) > max_length else text


# ── Endpoint ───────────────────────────────────────────────────────

@router.get("/search", response_model=SearchResponse)
async def global_search(
    q: str = Query(..., min_length=1, max_length=500),
    filter: Optional[str] = Query("all", alias="filter"),
    sort: str = Query("relevance"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(dependencies.get_db),
    redis: Redis = Depends(get_redis),
) -> Any:
    """Perform keyword search across published posts."""
    # Normalize query for better cache hit rate
    normalized_q = q.strip().lower()

    cache_params = dict(
        q=normalized_q, filter=filter or "all",
        sort=sort, skip=skip, limit=limit,
    )

    cached = await cache_get(redis, "search", **cache_params)
    if cached:
        return SearchResponse(**json.loads(cached))

    posts, total = await search_posts(
        db,
        q=q,
        category_filter=filter,
        sort=sort,
        skip=skip,
        limit=limit,
    )

    items = [
        SearchResultItem(
            id=p.id,
            title=p.title,
            slug=p.slug,
            excerpt=_build_excerpt(p.content),
            highlight=_build_excerpt(p.content, max_length=150),
            category=p.category,
            author=p.author,
            published_at=p.created_at,
            relevance_score=None,  # Requires vector similarity for real scoring
        )
        for p in posts
    ]
    response = SearchResponse(total=total, items=items)

    await cache_set(
        redis, "search",
        response.model_dump_json(),
        ttl=settings.CACHE_TTL_SEARCH,
        **cache_params,
    )
    return response
