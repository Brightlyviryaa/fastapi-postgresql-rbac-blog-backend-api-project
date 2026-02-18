import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.exc import PasswordSizeError
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.api import dependencies
from app.core import security
from app.core.config import settings

logger = logging.getLogger(__name__)

# Maximum password length to reject before hitting passlib internals.
MAX_LOGIN_PASSWORD_LENGTH = 1024

router = APIRouter()


@router.post("/login/access-token", response_model=schemas.Token)
async def login_access_token(
    db: AsyncSession = Depends(dependencies.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    # Guard against oversized passwords (DoS / passlib crash).
    if len(form_data.password) > MAX_LOGIN_PASSWORD_LENGTH:
        logger.warning(
            "Rejected oversized password (len=%d) for email=%s",
            len(form_data.password),
            form_data.username,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    try:
        user = await crud.user.authenticate(
            db, email=form_data.username, password=form_data.password
        )
    except PasswordSizeError:
        logger.warning(
            "PasswordSizeError during auth for email=%s",
            form_data.username,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    if not user:
        # Run dummy hash verification to prevent timing-based user enumeration.
        try:
            security.verify_password_dummy(form_data.password)
        except PasswordSizeError:
            pass
        logger.warning(
            "Failed login attempt for email=%s",
            form_data.username,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    if not crud.user.is_active(user):
        logger.warning(
            "Login attempt for inactive user id=%s email=%s",
            user.id,
            user.email,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )

    logger.info("Successful login for user id=%s", user.id)

    return {"access_token": access_token, "token_type": "bearer"}
