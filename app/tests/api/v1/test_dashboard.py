"""
Unit tests for Dashboard API endpoints.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.tests.conftest import override_auth, clear_overrides, make_mock_user


@pytest.fixture
def admin_user():
    return make_mock_user(role_name="admin", is_superuser=True)


@pytest.fixture
def redis_mock():
    # Helper to spy on cache usage if needed
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    mock.incr = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_dashboard_stats(client: AsyncClient, admin_user):
    """GET /dashboard/stats — happy path."""
    override_auth(admin_user, role_name="admin")
    
    # Mock the CRUD helper
    with patch("app.api.v1.endpoints.dashboard.get_dashboard_stats") as mock_get:
        mock_get.return_value = {
            "total_articles": 10,
            "published_articles": 5,
            "draft_articles": 5,
            "total_views": 100,
            "views_trend": None,
        }
        
        response = await client.get("/api/v1/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_articles"] == 10
        
    clear_overrides()


@pytest.mark.asyncio
async def test_dashboard_stats_non_admin(client: AsyncClient):
    """GET /dashboard/stats — 403 for non-admin."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")
    
    response = await client.get("/api/v1/dashboard/stats")
    assert response.status_code == 403
    
    clear_overrides()


@pytest.mark.asyncio
async def test_dashboard_stats_unauthenticated(client: AsyncClient):
    """GET /dashboard/stats — 401/403 for unauthenticated."""
    clear_overrides()
    response = await client.get("/api/v1/dashboard/stats")
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_dashboard_posts(client: AsyncClient, admin_user):
    """GET /dashboard/posts — happy path."""
    override_auth(admin_user, role_name="admin")
    
    with patch("app.api.v1.endpoints.dashboard.get_dashboard_posts") as mock_get:
        # Mock returns (posts_list, total_count)
        mock_post = AsyncMock()
        mock_post.id = 1
        mock_post.title = "Test Post"
        mock_post.slug = "test-post"
        mock_post.status = "published"
        mock_post.view_count = 10
        mock_post.created_at = "2024-01-01T00:00:00"
        mock_post.updated_at = "2024-01-01T00:00:00"
        
        # Nested mocks must have values for Pydantic validation
        mock_post.category = AsyncMock()
        mock_post.category.name = "Tech"
        
        mock_post.author = AsyncMock()
        mock_post.author.full_name = "Test Author"
        
        mock_get.return_value = ([mock_post], 1)
        
        response = await client.get("/api/v1/dashboard/posts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Test Post"

        
    clear_overrides()


@pytest.mark.asyncio
async def test_dashboard_posts_non_admin(client: AsyncClient):
    """GET /dashboard/posts — 403 for non-admin."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")
    
    response = await client.get("/api/v1/dashboard/posts")
    assert response.status_code == 403
    
    clear_overrides()


@pytest.mark.asyncio
async def test_dashboard_posts_negative_skip(client: AsyncClient, admin_user):
    """GET /dashboard/posts — validate paging params."""
    override_auth(admin_user, role_name="admin")
    
    response = await client.get("/api/v1/dashboard/posts?skip=-1")
    assert response.status_code == 422
    
    clear_overrides()


@pytest.mark.asyncio
async def test_dashboard_posts_sqli_in_status(client: AsyncClient, admin_user):
    """GET /dashboard/posts — attempt SQLi in string filter."""
    override_auth(admin_user, role_name="admin")

    with patch("app.api.v1.endpoints.dashboard.get_dashboard_posts") as mock_get:
        mock_get.return_value = ([], 0)
        
        # Pydantic checks alias="status"
        response = await client.get("/api/v1/dashboard/posts?status='; DROP TABLE users;--")
        # Should just pass through as string literal filter, returning empty list
        assert response.status_code == 200
        
    clear_overrides()


@pytest.mark.asyncio
async def test_dashboard_posts_oversized_category(client: AsyncClient, admin_user):
    """GET /dashboard/posts — attempt oversized string."""
    override_auth(admin_user, role_name="admin")

    with patch("app.api.v1.endpoints.dashboard.get_dashboard_posts") as mock_get:
        mock_get.return_value = ([], 0)
        huge_str = "a" * 10000
        response = await client.get(f"/api/v1/dashboard/posts?category={huge_str}")
        assert response.status_code == 200
        
    clear_overrides()


@pytest.mark.asyncio
async def test_dashboard_stats_no_sensitive_data(client: AsyncClient, admin_user):
    """GET /dashboard/stats — ensure no leakage."""
    override_auth(admin_user, role_name="admin")
    
    with patch("app.api.v1.endpoints.dashboard.get_dashboard_stats") as mock_get:
        mock_get.return_value = {
            "total_articles": 1, 
            "published_articles": 1, 
            "draft_articles": 0, 
            "total_views": 0,
            "views_trend": None
        }
        
        response = await client.get("/api/v1/dashboard/stats")
        text = response.text.lower()
        assert "password" not in text
        assert "connection" not in text

    clear_overrides()
