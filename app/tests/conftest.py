import pytest
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator
from unittest.mock import MagicMock, AsyncMock
from app.main import app
from app.api import dependencies
from app.db.session import get_db


class MockAsyncSession:
    """Minimal mock async session that satisfies RoleChecker's DB query."""

    def __init__(self, role_name: str = "admin"):
        self._role_name = role_name

    async def execute(self, stmt, *args, **kwargs):
        """Return a mock result set with a mock Role."""
        role = MagicMock()
        role.id = 1
        role.name = self._role_name
        role.description = f"{self._role_name} role"

        result = MagicMock()
        result.scalars.return_value.first.return_value = role
        return result

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def make_mock_user(
    user_id: int = 1,
    role_name: str = "editor",
    is_superuser: bool = False,
    is_active: bool = True,
):
    """Create a mock user with role for dependency injection."""
    user = MagicMock()
    user.id = user_id
    user.email = f"user{user_id}@example.com"
    user.full_name = f"User {user_id}"
    user.is_active = is_active
    user.is_superuser = is_superuser
    user.role_id = 1

    role = MagicMock()
    role.name = role_name
    user.role = role
    return user


def override_auth(user, role_name: str = "editor"):
    """Set up FastAPI dependency overrides for auth + DB so tests bypass JWT and DB."""
    app.dependency_overrides[dependencies.get_current_user] = lambda: user
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: user

    async def mock_get_db():
        yield MockAsyncSession(role_name=role_name)

    app.dependency_overrides[get_db] = mock_get_db


def clear_overrides():
    """Remove all dependency overrides."""
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
