"""Posts API endpoints."""
import json
import logging
from typing import Any, Optional

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

# RBAC guards
allow_editor = RoleChecker(["admin", "editor"])


# ── List Posts ──────────────────────────────────────────────────────

@router.get("/posts", response_model=schemas.PostListResponse)
async def list_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    category_slug: Optional[str] = None,
    tag_slug: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(dependencies.get_db),
    redis: Redis = Depends(get_redis),
) -> Any:
    """Retrieve paginated list of posts with optional filters."""
    cache_params = dict(
        skip=skip, limit=limit,
        status=status_filter or "",
        category=category_slug or "",
        tag=tag_slug or "",
        search=search or "",
    )

    cached = await cache_get(redis, "posts_list", **cache_params)
    if cached:
        return schemas.PostListResponse(**json.loads(cached))

    items, total = await crud.post.get_multi_with_filters(
        db,
        skip=skip,
        limit=limit,
        status=status_filter,
        category_slug=category_slug,
        tag_slug=tag_slug,
        search=search,
    )
    response = schemas.PostListResponse(total=total, items=items)

    await cache_set(
        redis,
        "posts_list",
        response.model_dump_json(),
        ttl=settings.CACHE_TTL_POSTS_LIST,
        **cache_params,
    )
    return response


# ── Get Post Detail ─────────────────────────────────────────────────

@router.get("/posts/{slug}", response_model=schemas.PostDetail)
async def get_post(
    slug: str,
    db: AsyncSession = Depends(dependencies.get_db),
    redis: Redis = Depends(get_redis),
) -> Any:
    """Retrieve a single post by slug."""
    cached = await cache_get(redis, "post_detail", slug=slug)
    if cached:
        return schemas.PostDetail(**json.loads(cached))

    post = await crud.post.get_by_slug(db, slug=slug)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    
    # Serialize manually since it returns a DB model, not Pydantic yet
    response = schemas.PostDetail.model_validate(post)

    await cache_set(
        redis,
        "post_detail",
        response.model_dump_json(),
        ttl=settings.CACHE_TTL_POST_DETAIL,
        slug=slug,
    )
    return response


# ── Create Post ─────────────────────────────────────────────────────

@router.post("/posts", response_model=schemas.PostDetail)
async def create_post(
    post_in: schemas.PostCreate,
    db: AsyncSession = Depends(dependencies.get_db),
    redis: Redis = Depends(get_redis),
    current_user=Depends(allow_editor),
) -> Any:
    """Create a new post. Requires editor role."""
    try:
        post = await crud.post.create_with_tags(
            db,
            obj_in=post_in,
            author_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    
    # Invalidate related caches
    await cache_invalidate(
        redis,
        "posts_list", 
        "search", 
        "dashboard_stats", 
        "dashboard_posts",
        "categories", # Counts change
        "tags",       # If new tags added
    )
    
    return post


# ── Update Post ─────────────────────────────────────────────────────

@router.put("/posts/{post_id}", response_model=schemas.PostDetail)
async def update_post(
    post_id: int,
    post_in: schemas.PostUpdate,
    db: AsyncSession = Depends(dependencies.get_db),
    redis: Redis = Depends(get_redis),
    current_user=Depends(allow_editor),
) -> Any:
    """Update an existing post. Editors can only update their own posts; admins can update any."""
    post = await crud.post.get(db, id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    # IDOR protection: editors can only update their own posts.
    if not current_user.is_superuser and post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to update this post",
        )
    try:
        original_slug = post.slug
        post = await crud.post.update_with_tags(db, db_obj=post, obj_in=post_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    
    # Invalidate related caches
    await cache_invalidate(
        redis, 
        "posts_list", 
        "post_detail", 
        "search", 
        "dashboard_stats", 
        "dashboard_posts",
        "categories",
        "tags"
    )
    
    return post


# ── Delete Post ─────────────────────────────────────────────────────

@router.delete("/posts/{post_id}", response_model=schemas.Post)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(dependencies.get_db),
    redis: Redis = Depends(get_redis),
    current_user=Depends(allow_editor),
) -> Any:
    """Soft-delete a post. Editors can only delete their own posts; admins can delete any."""
    post = await crud.post.get(db, id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    # IDOR protection.
    if not current_user.is_superuser and post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to delete this post",
        )
    post = await crud.post.soft_delete(db, db_obj=post)

    # Invalidate related caches
    await cache_invalidate(
        redis, 
        "posts_list", 
        "post_detail", 
        "search", 
        "dashboard_stats", 
        "dashboard_posts",
        "categories",
        "tags"
    )

    return post
