from typing import Generator, List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.core import security
from app.core.config import settings
from app.db.session import get_db

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> models.User:
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
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_superuser(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user


class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: models.User = Depends(get_current_active_user)):
        if user.is_superuser:
            return user
        # Check if user has a role and if that role is in allowed_roles
        # Note: This assumes eager loading of role, or we might need to load it.
        # Ideally, role_id is on user, so we can check role name via relationship if loaded,
        # or fetch role. For simplicity, assuming eager load or we fetch it.
        # Actually, `crud.user.get` doesn't eager load by default in base.
        # We might need to adjust `get` or just rely on lazy loading if async supports it (it doesn't well).
        # Better to check role_id or fetch role.
        # Let's assume we rely on `user.role` being available.
        # If not, we should probably fetch it.
        # For now, let's just check if user.role.name in allowed_roles if relationship is loaded.
        # If we run into MissingGreenlet, we'll need to use specific crud method with joinedload.
        
        # Safe approach: check role in DB
        # But we don't have async db session here directly in __call__ unless we inject it?
        # Typically we inject Dependencies in __call__.
        pass 

# Since RoleChecker as a class based dependency is a bit complex with Async and simple call, 
# let's define a factory or just simple function dependencies for specific roles if needed,
# OR implement it properly by injecting DB.

async def get_current_user_with_role(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> models.User:
    # ... (same as get_current_user but with joinedload if needed)
    # For now, let's stick to simple get_current_user and handle role check in endpoint or separate dependency
    pass

# Better RoleChecker implementation
class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user: models.User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
        if user.is_superuser:
            return user
        
        # Fetch role if not loaded
        # Since we are in async, accessing user.role might fail if not loaded.
        # We can query role by user.role_id
        if not user.role_id:
             raise HTTPException(status_code=403, detail="Operation not permitted")
        
        # We need to import CRUD for Role or just execute query
        from sqlalchemy import select
        from app.models.role import Role
        
        result = await db.execute(select(Role).filter(Role.id == user.role_id))
        role = result.scalars().first()
        
        if not role or role.name not in self.allowed_roles:
            raise HTTPException(status_code=403, detail="Operation not permitted")
        return user
