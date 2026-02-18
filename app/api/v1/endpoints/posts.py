"""Posts API endpoints."""
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.api import dependencies
from app.api.dependencies import RoleChecker

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
) -> Any:
    """Retrieve paginated list of posts with optional filters."""
    items, total = await crud.post.get_multi_with_filters(
        db,
        skip=skip,
        limit=limit,
        status=status_filter,
        category_slug=category_slug,
        tag_slug=tag_slug,
        search=search,
    )
    return {"total": total, "items": items}


# ── Get Post Detail ─────────────────────────────────────────────────

@router.get("/posts/{slug}", response_model=schemas.PostDetail)
async def get_post(
    slug: str,
    db: AsyncSession = Depends(dependencies.get_db),
) -> Any:
    """Retrieve a single post by slug."""
    post = await crud.post.get_by_slug(db, slug=slug)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    return post


# ── Create Post ─────────────────────────────────────────────────────

@router.post("/posts", response_model=schemas.PostDetail)
async def create_post(
    post_in: schemas.PostCreate,
    db: AsyncSession = Depends(dependencies.get_db),
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
    return post


# ── Update Post ─────────────────────────────────────────────────────

@router.put("/posts/{post_id}", response_model=schemas.PostDetail)
async def update_post(
    post_id: int,
    post_in: schemas.PostUpdate,
    db: AsyncSession = Depends(dependencies.get_db),
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
        post = await crud.post.update_with_tags(db, db_obj=post, obj_in=post_in)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return post


# ── Delete Post ─────────────────────────────────────────────────────

@router.delete("/posts/{post_id}", response_model=schemas.Post)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(dependencies.get_db),
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
    return post
