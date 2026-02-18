"""Taxonomy API endpoints (Categories + Tags)."""
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.api import dependencies
from app.api.dependencies import RoleChecker

logger = logging.getLogger(__name__)

router = APIRouter()

# RBAC guard for write operations
allow_editor = RoleChecker(["admin", "editor"])


# ── Categories ──────────────────────────────────────────────────────

@router.get("/categories", response_model=List[schemas.CategoryWithCount])
async def list_categories(
    db: AsyncSession = Depends(dependencies.get_db),
) -> Any:
    """Retrieve all categories with post counts."""
    return await crud.category.get_multi_with_count(db)


@router.post("/categories", response_model=schemas.Category)
async def create_category(
    category_in: schemas.CategoryCreate,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user=Depends(allow_editor),
) -> Any:
    """Create a new category. Requires editor/admin role."""
    existing = await crud.category.get_by_slug(db, slug=category_in.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A category with this slug already exists",
        )
    return await crud.category.create(db, obj_in=category_in)


# ── Tags ────────────────────────────────────────────────────────────

@router.get("/tags", response_model=List[schemas.Tag])
async def list_tags(
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(dependencies.get_db),
) -> Any:
    """Retrieve tags, optionally filtered by search query for autocomplete."""
    return await crud.tag.get_multi_filtered(db, q=q)


@router.post("/tags", response_model=schemas.Tag)
async def create_tag(
    tag_in: schemas.TagCreate,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user=Depends(allow_editor),
) -> Any:
    """Create a new tag. Requires editor/admin role."""
    existing = await crud.tag.get_by_slug(db, slug=tag_in.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A tag with this slug already exists",
        )
    return await crud.tag.create(db, obj_in=tag_in)
