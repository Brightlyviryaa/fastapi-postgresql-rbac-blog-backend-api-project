"""
Unit tests for the Analytics / Dashboard API endpoints.

Covers:
  - Happy paths (get stats, list dashboard posts)
  - Error cases (403 non-admin)
  - Security / Penetration (SQLi in filter, oversized params)
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.tests.conftest import make_mock_user, override_auth, clear_overrides


# ── Helpers ─────────────────────────────────────────────────────────

def _make_mock_dashboard_post(
    post_id: int = 1,
    title: str = "Test Post",
    slug: str = "test-post",
    status: str = "published",
    views: int = 1200,
):
    post = MagicMock()
    post.id = post_id
    post.title = title
    post.slug = slug
    post.status = status
    post.view_count = views
    post.created_at = datetime(2026, 2, 18, tzinfo=timezone.utc)
    post.updated_at = datetime(2026, 2, 18, tzinfo=timezone.utc)

    cat = MagicMock()
    cat.id = 1
    cat.name = "AI & Ethics"
    cat.slug = "ai-ethics"
    post.category = cat

    author = MagicMock()
    author.id = 1
    author.full_name = "Jonathan Doe"
    post.author = author

    return post


# ── Dashboard Stats (Happy) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_stats(client: AsyncClient):
    """GET /dashboard/stats — 200, returns article counts and views."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    mock_stats = {
        "total_articles": 142,
        "published_articles": 128,
        "draft_articles": 14,
        "total_views": 45000,
        "views_trend": None,
    }

    try:
        with patch(
            "app.api.v1.endpoints.dashboard.get_dashboard_stats",
            new_callable=AsyncMock,
            return_value=mock_stats,
        ):
            response = await client.get("/api/v1/dashboard/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["total_articles"] == 142
            assert data["published_articles"] == 128
            assert data["draft_articles"] == 14
            assert data["total_views"] == 45000
    finally:
        clear_overrides()


# ── Dashboard Stats (Error) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_stats_non_admin(client: AsyncClient):
    """GET /dashboard/stats — 403 for non-admin users."""
    user = make_mock_user(role_name="viewer")
    override_auth(user, role_name="viewer")

    try:
        response = await client.get("/api/v1/dashboard/stats")
        assert response.status_code == 403
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_dashboard_stats_unauthenticated(client: AsyncClient):
    """GET /dashboard/stats — 401/403 without auth."""
    clear_overrides()
    response = await client.get("/api/v1/dashboard/stats")
    assert response.status_code in (401, 403)


# ── Dashboard Posts (Happy) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_posts(client: AsyncClient):
    """GET /dashboard/posts — 200, paginated admin post list."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    mock_post = _make_mock_dashboard_post()

    try:
        with patch(
            "app.api.v1.endpoints.dashboard.get_dashboard_posts",
            new_callable=AsyncMock,
            return_value=([mock_post], 1),
        ):
            response = await client.get("/api/v1/dashboard/posts")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["title"] == "Test Post"
    finally:
        clear_overrides()


# ── Dashboard Posts (Error) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_posts_non_admin(client: AsyncClient):
    """GET /dashboard/posts — 403 for non-admin."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")

    try:
        response = await client.get("/api/v1/dashboard/posts")
        assert response.status_code == 403
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_dashboard_posts_negative_skip(client: AsyncClient):
    """GET /dashboard/posts?skip=-1 — 422 invalid pagination."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    try:
        response = await client.get("/api/v1/dashboard/posts", params={"skip": -1})
        assert response.status_code == 422
    finally:
        clear_overrides()


# ── Security: SQL Injection ────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_posts_sqli_in_status(client: AsyncClient):
    """GET /dashboard/posts?status='; DROP TABLE posts;-- — treated literally."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    try:
        with patch(
            "app.api.v1.endpoints.dashboard.get_dashboard_posts",
            new_callable=AsyncMock,
            return_value=([], 0),
        ):
            response = await client.get(
                "/api/v1/dashboard/posts",
                params={"status": "'; DROP TABLE posts; --"},
            )
            # Should be 200 with empty results, NOT a 500
            assert response.status_code == 200
    finally:
        clear_overrides()


# ── Security: Oversized Params ─────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_posts_oversized_category(client: AsyncClient):
    """GET /dashboard/posts?category=aaa...aaa — handled gracefully."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    try:
        with patch(
            "app.api.v1.endpoints.dashboard.get_dashboard_posts",
            new_callable=AsyncMock,
            return_value=([], 0),
        ):
            response = await client.get(
                "/api/v1/dashboard/posts",
                params={"category": "a" * 5000},
            )
            assert response.status_code == 200
    finally:
        clear_overrides()


# ── Security: Response Data Leakage ───────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_stats_no_sensitive_data(client: AsyncClient):
    """GET /dashboard/stats — response must not leak internals."""
    user = make_mock_user(role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")

    mock_stats = {
        "total_articles": 10,
        "published_articles": 8,
        "draft_articles": 2,
        "total_views": 500,
        "views_trend": None,
    }

    try:
        with patch(
            "app.api.v1.endpoints.dashboard.get_dashboard_stats",
            new_callable=AsyncMock,
            return_value=mock_stats,
        ):
            response = await client.get("/api/v1/dashboard/stats")
            assert response.status_code == 200
            text = response.text.lower()
            assert "password" not in text
            assert "hashed" not in text
    finally:
        clear_overrides()
