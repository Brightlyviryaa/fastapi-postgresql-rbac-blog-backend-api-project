from datetime import datetime, timedelta, timezone
from typing import Any, Union

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pre-computed dummy hash for constant-time verification on unknown users.
# This prevents timing-based user enumeration attacks.
_DUMMY_HASH = pwd_context.hash("__dummy_placeholder__")


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta | None = None
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def verify_password_dummy(plain_password: str) -> None:
    """Run a dummy bcrypt verification to equalise response time
    when the user does not exist. Result is intentionally discarded."""
    try:
        pwd_context.verify(plain_password, _DUMMY_HASH)
    except Exception:
        # Gracefully handle oversized passwords or any bcrypt errors.
        # The sole purpose is timing equalisation; the result is discarded.
        pass


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
