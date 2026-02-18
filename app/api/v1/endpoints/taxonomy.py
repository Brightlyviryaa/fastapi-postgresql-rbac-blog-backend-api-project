"""Taxonomy API endpoints (Categories + Tags)."""
import json
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.api import dependencies
from app.api.dependencies import RoleChecker
from app.core.cache import cache_get, cache_invalidate, cache_set
from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

router = APIRouter()

# RBAC guard for write operations
allow_editor = RoleChecker(["admin", "editor"])


# ── Categories ──────────────────────────────────────────────────────

@router.get("/categories", response_model=List[schemas.CategoryWithCount])
async def list_categories(
    db: AsyncSession = Depends(dependencies.get_db),
    redis: Redis = Depends(get_redis),
) -> Any:
    """Retrieve all categories with post counts."""
    # Cache all categories (no params needed for key)
    cached = await cache_get(redis, "categories")
    if cached:
        # Deserialize JSON list -> Pydantic models
        data = json.loads(cached)
        return [schemas.CategoryWithCount(**item) for item in data]

    items = await crud.category.get_multi_with_count(db)
    
    # Manually serialize list of Pydantic models
    # items are dicts from crud, so we validate them first
    data = [schemas.CategoryWithCount(**item) for item in items]
    json_str = json.dumps([item.model_dump() for item in data], default=str)

    await cache_set(
        redis,
        "categories",
        json_str,
        ttl=settings.CACHE_TTL_CATEGORIES,
    )
    return items


@router.post("/categories", response_model=schemas.Category)
async def create_category(
    category_in: schemas.CategoryCreate,
    db: AsyncSession = Depends(dependencies.get_db),
    redis: Redis = Depends(get_redis),
    current_user=Depends(allow_editor),
) -> Any:
    """Create a new category. Requires editor/admin role."""
    existing = await crud.category.get_by_slug(db, slug=category_in.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A category with this slug already exists",
        )
    category = await crud.category.create(db, obj_in=category_in)
    
    # Invalidate categories and search (new category available for filter)
    await cache_invalidate(redis, "categories", "search")
    
    return category


# ── Tags ────────────────────────────────────────────────────────────

@router.get("/tags", response_model=List[schemas.Tag])
async def list_tags(
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(dependencies.get_db),
    redis: Redis = Depends(get_redis),
) -> Any:
    """Retrieve tags, optionally filtered by search query for autocomplete."""
    cache_params = dict(q=q or "")
    
    cached = await cache_get(redis, "tags", **cache_params)
    if cached:
        data = json.loads(cached)
        return [schemas.Tag(**item) for item in data]

    items = await crud.tag.get_multi_filtered(db, q=q)
    
    json_str = json.dumps([item.model_dump() for item in items], default=str)
    
    await cache_set(
        redis,
        "tags",
        json_str,
        ttl=settings.CACHE_TTL_TAGS,
        **cache_params,
    )
    return items


@router.post("/tags", response_model=schemas.Tag)
async def create_tag(
    tag_in: schemas.TagCreate,
    db: AsyncSession = Depends(dependencies.get_db),
    redis: Redis = Depends(get_redis),
    current_user=Depends(allow_editor),
) -> Any:
    """Create a new tag. Requires editor/admin role."""
    existing = await crud.tag.get_by_slug(db, slug=tag_in.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A tag with this slug already exists",
        )
    tag = await crud.tag.create(db, obj_in=tag_in)
    
    # Invalidate tags
    await cache_invalidate(redis, "tags")

    return tag
