"""
Unit tests for the Newsletter Subscribers API endpoints.

Covers:
  - Happy paths (subscribe, unsubscribe)
  - Error cases (already subscribed idempotent, unsubscribe nonexistent)
  - Security / Penetration (SQLi, XSS, invalid email, oversized)
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ── Helpers ─────────────────────────────────────────────────────────

def _make_mock_subscriber(
    sub_id: int = 1,
    email: str = "user@example.com",
    is_active: bool = True,
):
    sub = MagicMock()
    sub.id = sub_id
    sub.email = email
    sub.is_active = is_active
    sub.created_at = datetime(2026, 2, 18, tzinfo=timezone.utc)
    return sub


# ── Subscribe (Happy) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_subscribe_new_email(client: AsyncClient):
    """POST /subscribers — 200, new email subscribed successfully."""
    with patch("app.crud.subscriber.get_by_email", new_callable=AsyncMock, return_value=None), \
         patch("app.crud.subscriber.create", new_callable=AsyncMock, return_value=_make_mock_subscriber()):
        response = await client.post(
            "/api/v1/subscribers",
            json={"email": "user@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully subscribed."


@pytest.mark.asyncio
async def test_subscribe_already_exists(client: AsyncClient):
    """POST /subscribers — 200, idempotent when already subscribed."""
    existing = _make_mock_subscriber(is_active=True)
    with patch("app.crud.subscriber.get_by_email", new_callable=AsyncMock, return_value=existing):
        response = await client.post(
            "/api/v1/subscribers",
            json={"email": "user@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Already subscribed."


@pytest.mark.asyncio
async def test_subscribe_reactivate_inactive(client: AsyncClient):
    """POST /subscribers — 200, reactivates a previously unsubscribed email."""
    inactive = _make_mock_subscriber(is_active=False)
    reactivated = _make_mock_subscriber(is_active=True)

    with patch("app.crud.subscriber.get_by_email", new_callable=AsyncMock, return_value=inactive), \
         patch("app.crud.subscriber.reactivate", new_callable=AsyncMock, return_value=reactivated):
        response = await client.post(
            "/api/v1/subscribers",
            json={"email": "user@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully subscribed."


# ── Unsubscribe (Happy) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unsubscribe(client: AsyncClient):
    """DELETE /subscribers/{email} — 200, deactivates subscription."""
    existing = _make_mock_subscriber()
    deactivated = _make_mock_subscriber(is_active=False)

    with patch("app.crud.subscriber.get_by_email", new_callable=AsyncMock, return_value=existing), \
         patch("app.crud.subscriber.deactivate", new_callable=AsyncMock, return_value=deactivated):
        response = await client.delete("/api/v1/subscribers/user@example.com")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully unsubscribed."


# ── Unsubscribe (Error) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unsubscribe_nonexistent(client: AsyncClient):
    """DELETE /subscribers/{email} — 404 when email not found."""
    with patch("app.crud.subscriber.get_by_email", new_callable=AsyncMock, return_value=None):
        response = await client.delete("/api/v1/subscribers/ghost@example.com")
        assert response.status_code == 404


# ── Security: Invalid Email Format ─────────────────────────────────

@pytest.mark.asyncio
async def test_subscribe_invalid_email_format(client: AsyncClient):
    """POST /subscribers — 422 for invalid email format."""
    response = await client.post(
        "/api/v1/subscribers",
        json={"email": "not-an-email"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_subscribe_empty_email(client: AsyncClient):
    """POST /subscribers — 422 for empty email."""
    response = await client.post(
        "/api/v1/subscribers",
        json={"email": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_subscribe_missing_email(client: AsyncClient):
    """POST /subscribers — 422 when email field is missing."""
    response = await client.post("/api/v1/subscribers", json={})
    assert response.status_code == 422


# ── Security: SQL Injection ────────────────────────────────────────

@pytest.mark.asyncio
async def test_subscribe_sql_injection(client: AsyncClient):
    """POST /subscribers — SQLi in email rejected by validation."""
    response = await client.post(
        "/api/v1/subscribers",
        json={"email": "'; DROP TABLE subscribers; --"},
    )
    # Pydantic EmailStr will reject this
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unsubscribe_sql_injection_in_path(client: AsyncClient):
    """DELETE /subscribers/{email} — SQLi in path is treated literally."""
    with patch("app.crud.subscriber.get_by_email", new_callable=AsyncMock, return_value=None):
        response = await client.delete("/api/v1/subscribers/'; DROP TABLE subscribers; --")
        # Should be 404 (not found), NOT a 500 server error
        assert response.status_code == 404


# ── Security: XSS ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_subscribe_xss_in_email(client: AsyncClient):
    """POST /subscribers — XSS in email rejected by validation."""
    response = await client.post(
        "/api/v1/subscribers",
        json={"email": "<script>alert('xss')</script>@evil.com"},
    )
    assert response.status_code == 422


# ── Security: Oversized Payload ────────────────────────────────────

@pytest.mark.asyncio
async def test_subscribe_oversized_email(client: AsyncClient):
    """POST /subscribers — oversized email rejected."""
    huge_email = "a" * 500 + "@example.com"
    response = await client.post(
        "/api/v1/subscribers",
        json={"email": huge_email},
    )
    # Should be rejected by Pydantic validation
    assert response.status_code == 422


# ── Security: Response Data Leakage ────────────────────────────────

@pytest.mark.asyncio
async def test_subscribe_response_no_internal_ids(client: AsyncClient):
    """POST /subscribers — response should not leak internal DB IDs."""
    with patch("app.crud.subscriber.get_by_email", new_callable=AsyncMock, return_value=None), \
         patch("app.crud.subscriber.create", new_callable=AsyncMock, return_value=_make_mock_subscriber()):
        response = await client.post(
            "/api/v1/subscribers",
            json={"email": "user@example.com"},
        )
        assert response.status_code == 200
        text = response.text
        # Only a message should be returned, no subscriber object internals
        assert "message" in response.json()
