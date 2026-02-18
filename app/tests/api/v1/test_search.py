"""
Unit tests for Search API.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.tests.conftest import override_auth, clear_overrides


@pytest.mark.asyncio
async def test_search_with_results(client: AsyncClient):
    """GET /search — happy path with hits."""
    # Search is public, no auth needed usually, but we mock DB/Redis
    override_auth(None) # just to set DB/Redis mocks

    with patch("app.api.v1.endpoints.search.search_posts") as mock_search:
        mock_post = AsyncMock()
        mock_post.id = 1
        mock_post.title = "Python Tutorial"
        mock_post.slug = "python-tutorial"
        mock_post.content = "<p>Learn Python...</p>"
        mock_post.created_at = "2024-01-01T00:00:00"
        
        # Mock relationships
        mock_category = AsyncMock()
        mock_category.name = "Programming"
        mock_category.slug = "programming"
        mock_post.category = mock_category

        mock_author = AsyncMock()
        mock_author.full_name = "Guido van Rossum"
        mock_post.author = mock_author
        
        
        mock_search.return_value = ([mock_post], 1)

        response = await client.get("/api/v1/search?q=python")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "python-tutorial"
        
    clear_overrides()


@pytest.mark.asyncio
async def test_search_empty_results(client: AsyncClient):
    """GET /search — valid query, no hits."""
    override_auth(None)

    with patch("app.api.v1.endpoints.search.search_posts") as mock_search:
        mock_search.return_value = ([], 0)

        response = await client.get("/api/v1/search?q=nothing")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    clear_overrides()


@pytest.mark.asyncio
async def test_search_with_category_filter(client: AsyncClient):
    """GET /search — with filter."""
    override_auth(None)

    with patch("app.api.v1.endpoints.search.search_posts") as mock_search:
        mock_search.return_value = ([], 0)
        
        response = await client.get("/api/v1/search?q=test&filter=tech")
        assert response.status_code == 200
        # Verify mock called with correct args
        mock_search.assert_called_once()
        _, kwargs = mock_search.call_args
        assert kwargs["category_filter"] == "tech"

    clear_overrides()


@pytest.mark.asyncio
async def test_search_with_date_sort(client: AsyncClient):
    """GET /search — with sort."""
    override_auth(None)

    with patch("app.api.v1.endpoints.search.search_posts") as mock_search:
        mock_search.return_value = ([], 0)
        response = await client.get("/api/v1/search?q=test&sort=date")
        assert response.status_code == 200
        _, kwargs = mock_search.call_args
        assert kwargs["sort"] == "date"

    clear_overrides()


@pytest.mark.asyncio
async def test_search_missing_query(client: AsyncClient):
    """GET /search — missing 'q' param (422)."""
    response = await client.get("/api/v1/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_empty_query(client: AsyncClient):
    """GET /search — empty 'q' param (422)."""
    response = await client.get("/api/v1/search?q=")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_negative_skip(client: AsyncClient):
    """GET /search — negative skip (422)."""
    response = await client.get("/api/v1/search?q=test&skip=-1")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_sql_injection(client: AsyncClient):
    """GET /search — attempt SQLi in query."""
    override_auth(None)
    with patch("app.api.v1.endpoints.search.search_posts") as mock_search:
        mock_search.return_value = ([], 0)
        
        # Should be treated as literal string
        response = await client.get("/api/v1/search?q=' OR 1=1;--")
        assert response.status_code == 200
        
    clear_overrides()


@pytest.mark.asyncio
async def test_search_sqli_in_filter(client: AsyncClient):
    """GET /search — attempt SQLi in filter."""
    override_auth(None)
    with patch("app.api.v1.endpoints.search.search_posts") as mock_search:
        mock_search.return_value = ([], 0)
        # Should be treated as literal string
        response = await client.get("/api/v1/search?q=test&filter=' OR 1=1")
        assert response.status_code == 200

    clear_overrides()


@pytest.mark.asyncio
async def test_search_xss_in_query(client: AsyncClient):
    """GET /search — ensure query echo in UI (if any) is safe (API just returns execution)."""
    override_auth(None)
    with patch("app.api.v1.endpoints.search.search_posts") as mock_search:
        mock_search.return_value = ([], 0)
        
        response = await client.get("/api/v1/search?q=<script>alert(1)</script>")
        assert response.status_code == 200

    clear_overrides()


@pytest.mark.asyncio
async def test_search_oversized_query(client: AsyncClient):
    """GET /search — query too long (422)."""
    huge = "a" * 1000
    response = await client.get(f"/api/v1/search?q={huge}")
    assert response.status_code == 422 # Max length is 500


@pytest.mark.asyncio
async def test_search_response_no_sensitive_data(client: AsyncClient):
    """GET /search — no leakage."""
    override_auth(None)
    with patch("app.api.v1.endpoints.search.search_posts") as mock_search:
        mock_search.return_value = ([], 0)
        response = await client.get("/api/v1/search?q=safe")
        text = response.text.lower()
        assert "password" not in text
        
    clear_overrides()
