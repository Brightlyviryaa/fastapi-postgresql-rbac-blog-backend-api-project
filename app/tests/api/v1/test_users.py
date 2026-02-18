"""
Unit tests for the Users API endpoints.

Covers:
  - Happy paths (list users, create user, get current user)
  - Error cases (403 non-superuser, 400 duplicate email)
  - Security / Penetration (SQLi, XSS, oversized payloads, data leakage)
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.tests.conftest import make_mock_user, override_auth, clear_overrides


# ── Helpers ─────────────────────────────────────────────────────────

def _make_mock_user_orm(
    user_id: int = 1,
    email: str = "user@example.com",
    full_name: str = "John Doe",
    is_active: bool = True,
    is_superuser: bool = False,
    role_name: str = "user",
):
    """Create a mock User ORM object."""
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.full_name = full_name
    user.is_active = is_active
    user.is_superuser = is_superuser
    user.role_id = 1

    role = MagicMock()
    role.id = 1
    role.name = role_name
    role.description = f"{role_name} role"
    user.role = role
    return user


# ── List Users (Happy) ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_as_superuser(client: AsyncClient):
    """GET /users/ — 200, superuser can list all users."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    mock_users = [_make_mock_user_orm(1), _make_mock_user_orm(2, email="user2@example.com")]

    try:
        with patch("app.crud.user.get_multi", new_callable=AsyncMock, return_value=mock_users):
            response = await client.get("/api/v1/users/")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["email"] == "user@example.com"
    finally:
        clear_overrides()


# ── List Users (Error) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_as_regular_user(client: AsyncClient):
    """GET /users/ — 403, non-superuser cannot list users."""
    clear_overrides()
    user = make_mock_user(role_name="viewer", is_superuser=False)
    override_auth(user, role_name="viewer")

    try:
        response = await client.get("/api/v1/users/")
        assert response.status_code == 403
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_list_users_unauthenticated(client: AsyncClient):
    """GET /users/ — 401/403 without auth token."""
    clear_overrides()
    response = await client.get("/api/v1/users/")
    assert response.status_code in (401, 403)


# ── Create User (Happy) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_as_superuser(client: AsyncClient):
    """POST /users/ — 200, superuser creates new user."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    new_user = _make_mock_user_orm(3, email="new@example.com", full_name="New User")

    try:
        with patch("app.crud.user.get_by_email", new_callable=AsyncMock, return_value=None), \
             patch("app.crud.user.create", new_callable=AsyncMock, return_value=new_user):
            response = await client.post(
                "/api/v1/users/",
                json={
                    "email": "new@example.com",
                    "password": "StrongP@ss123!",
                    "full_name": "New User",
                    "role_id": 1,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "new@example.com"
            assert "hashed_password" not in data
    finally:
        clear_overrides()


# ── Create User (Error) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient):
    """POST /users/ — 400 when email already exists."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    existing = _make_mock_user_orm(1, email="exists@example.com")

    try:
        with patch("app.crud.user.get_by_email", new_callable=AsyncMock, return_value=existing):
            response = await client.post(
                "/api/v1/users/",
                json={
                    "email": "exists@example.com",
                    "password": "StrongP@ss123!",
                    "full_name": "Duplicate",
                },
            )
            assert response.status_code == 400
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_create_user_as_non_superuser(client: AsyncClient):
    """POST /users/ — 403 for non-superuser."""
    user = make_mock_user(role_name="editor", is_superuser=False)
    override_auth(user, role_name="editor")

    try:
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "no@example.com",
                "password": "StrongP@ss123!",
                "full_name": "No Access",
            },
        )
        assert response.status_code == 403
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_create_user_missing_fields(client: AsyncClient):
    """POST /users/ — 422 when required fields are missing."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    try:
        response = await client.post("/api/v1/users/", json={})
        assert response.status_code == 422
    finally:
        clear_overrides()


# ── Get Current User (Happy) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    """GET /users/me — 200, returns current user."""
    user = make_mock_user(role_name="editor")
    # Ensure role attributes resolve to real strings for response serialization
    user.role.description = "editor role"
    override_auth(user, role_name="editor")

    try:
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user.email
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_get_current_user_unauthenticated(client: AsyncClient):
    """GET /users/me — 401/403 without auth."""
    clear_overrides()
    response = await client.get("/api/v1/users/me")
    assert response.status_code in (401, 403)


# ── Security: SQL Injection ────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_sql_injection_in_email(client: AsyncClient):
    """POST /users/ — SQLi in email treated as literal, rejected by validation."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    try:
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "'; DROP TABLE user; --",
                "password": "StrongP@ss123!",
                "full_name": "Hacker",
            },
        )
        # Should be rejected by Pydantic EmailStr validation
        assert response.status_code == 422
    finally:
        clear_overrides()


# ── Security: XSS ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_xss_in_full_name(client: AsyncClient):
    """POST /users/ — XSS in full_name should not crash and not execute."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    xss_name = "<script>alert('xss')</script>"
    new_user = _make_mock_user_orm(4, email="xss@example.com", full_name=xss_name)

    try:
        with patch("app.crud.user.get_by_email", new_callable=AsyncMock, return_value=None), \
             patch("app.crud.user.create", new_callable=AsyncMock, return_value=new_user):
            response = await client.post(
                "/api/v1/users/",
                json={
                    "email": "xss@example.com",
                    "password": "StrongP@ss123!",
                    "full_name": xss_name,
                },
            )
            # Should succeed (Pydantic doesn't sanitize names) but not crash
            assert response.status_code == 200
    finally:
        clear_overrides()


# ── Security: Oversized Payload ────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_oversized_password(client: AsyncClient):
    """POST /users/ — oversized password should not crash the system."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    try:
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "oversized@example.com",
                "password": "a" * 5000,
                "full_name": "Big Password",
            },
        )
        # Oversized password is rejected gracefully (400 by endpoint guard, or 422 by validation)
        assert response.status_code in (400, 422)
    finally:
        clear_overrides()


# ── Security: Data Leakage ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_response_no_password_leak(client: AsyncClient):
    """GET /users/ — response must never contain hashed_password."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    mock_user = _make_mock_user_orm()
    mock_user.hashed_password = "some_hashed_value"

    try:
        with patch("app.crud.user.get_multi", new_callable=AsyncMock, return_value=[mock_user]):
            response = await client.get("/api/v1/users/")
            assert response.status_code == 200
            text = response.text
            assert "hashed_password" not in text
            assert "some_hashed_value" not in text
    finally:
        clear_overrides()
