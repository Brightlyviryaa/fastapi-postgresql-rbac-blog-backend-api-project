from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.core.config import settings
from app.db.session import get_db  # noqa: F401 — re-exported for endpoint usage
from app.models.role import Role

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(reusable_oauth2),
) -> models.User:
    """Decode JWT and return the corresponding user."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = await crud.user.get(db, id=int(token_data.sub))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Require that the current JWT user is active."""
    if not crud.user.is_active(current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


def get_current_active_superuser(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Require that the current JWT user is a superuser."""
    if not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


class RoleChecker:
    """Dependency that enforces role-based access control.

    Usage::

        allow_editor = RoleChecker(["admin", "editor"])

        @router.get("/posts", dependencies=[Depends(allow_editor)])
        async def list_posts(): ...
    """

    def __init__(self, allowed_roles: List[str]) -> None:
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        user: models.User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> models.User:
        # Superusers bypass role checks.
        if user.is_superuser:
            return user

        if not user.role_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted",
            )

        result = await db.execute(select(Role).filter(Role.id == user.role_id))
        role = result.scalars().first()

        if not role or role.name not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted",
            )
        return user
