"""Comments API endpoints."""
import json
import logging
from typing import Any

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

# RBAC guard for admin-only actions
allow_admin = RoleChecker(["admin"])


# ── List Comments ───────────────────────────────────────────────────

@router.get(
    "/posts/{post_slug}/comments",
    response_model=schemas.CommentListResponse,
)
async def list_comments(
    post_slug: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(dependencies.get_db),
    redis: Redis = Depends(get_redis),
) -> Any:
    """Retrieve approved comments for a post (public)."""
    cache_params = dict(slug=post_slug, skip=skip, limit=limit)
    
    cached = await cache_get(redis, "comments", **cache_params)
    if cached:
        return schemas.CommentListResponse(**json.loads(cached))

    items, total = await crud.comment.get_by_post_slug(
        db, post_slug=post_slug, skip=skip, limit=limit,
    )
    response = schemas.CommentListResponse(total=total, items=items)

    await cache_set(
        redis,
        "comments",
        response.model_dump_json(),
        ttl=settings.CACHE_TTL_COMMENTS,
        **cache_params,
    )
    return response


# ── Create Comment ──────────────────────────────────────────────────

@router.post(
    "/posts/{post_slug}/comments",
    response_model=schemas.Comment,
)
async def create_comment(
    post_slug: str,
    comment_in: schemas.CommentCreate,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_active_user),
    redis: Redis = Depends(get_redis),
) -> Any:
    """Add a comment to a post. Requires authentication. Comment is pending approval."""
    post = await crud.post.get_by_slug(db, slug=post_slug)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    try:
        comment = await crud.comment.create_comment(
            db,
            content=comment_in.content,
            post_id=post.id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    
    # Invalidate comments list for this post
    await cache_invalidate(redis, "comments")
    
    return comment


# ── Approve Comment ─────────────────────────────────────────────────

@router.post(
    "/comments/{comment_id}/approve",
    response_model=schemas.Comment,
)
async def approve_comment(
    comment_id: int,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user=Depends(allow_admin),
    redis: Redis = Depends(get_redis),
) -> Any:
    """Approve a comment for public display. Admin only."""
    comment = await crud.comment.get(db, comment_id)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )
    comment = await crud.comment.approve(db, db_obj=comment)
    
    # Invalidate comments list
    await cache_invalidate(redis, "comments")

    return comment


# ── Delete Comment ──────────────────────────────────────────────────

@router.delete(
    "/comments/{comment_id}",
    response_model=schemas.Comment,
)
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user=Depends(dependencies.get_current_active_user),
    redis: Redis = Depends(get_redis),
) -> Any:
    """Delete a comment. Owner or admin."""
    comment = await crud.comment.get(db, comment_id)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )
    # Allow deletion only by the comment owner or a superuser/admin.
    if not current_user.is_superuser and comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to delete this comment",
        )
    comment = await crud.comment.remove(db, id=comment_id)
    
    # Invalidate comments list
    await cache_invalidate(redis, "comments")

    return comment
