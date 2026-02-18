"""
Unit tests for the Search API endpoint.

Covers:
  - Happy paths (search with results, filters, empty results)
  - Error cases (missing query, negative pagination)
  - Security / Penetration (SQLi, XSS, oversized query)
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ── Helpers ─────────────────────────────────────────────────────────

def _make_mock_search_result(
    post_id: int = 1,
    title: str = "Generative AI: The Hallucination is the Feature",
    slug: str = "generative-ai-hallucination",
):
    post = MagicMock()
    post.id = post_id
    post.title = title
    post.slug = slug
    post.content = "Mengapa mengejar akurasi sempurna dalam LLM..."
    post.abstract = "Mengapa mengejar akurasi sempurna..."
    post.status = "published"
    post.created_at = datetime(2026, 2, 18, tzinfo=timezone.utc)
    post.updated_at = datetime(2026, 2, 18, tzinfo=timezone.utc)

    cat = MagicMock()
    cat.name = "AI & Ethics"
    cat.slug = "ai-ethics"
    post.category = cat

    author = MagicMock()
    author.full_name = "Jonathan Doe"
    post.author = author

    return post


# ── Search (Happy) ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_with_results(client: AsyncClient):
    """GET /search?q=AI — 200, returns matching posts."""
    mock_result = _make_mock_search_result()
    with patch(
        "app.api.v1.endpoints.search.search_posts",
        new_callable=AsyncMock,
        return_value=([mock_result], 1),
    ):
        response = await client.get("/api/v1/search", params={"q": "AI"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert "AI" in data["items"][0]["title"]


@pytest.mark.asyncio
async def test_search_empty_results(client: AsyncClient):
    """GET /search?q=zzzznonexistent — 200, empty results."""
    with patch(
        "app.api.v1.endpoints.search.search_posts",
        new_callable=AsyncMock,
        return_value=([], 0),
    ):
        response = await client.get("/api/v1/search", params={"q": "zzzznonexistent"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


@pytest.mark.asyncio
async def test_search_with_category_filter(client: AsyncClient):
    """GET /search?q=AI&filter=ai-ethics — 200, filtered by category."""
    mock_result = _make_mock_search_result()
    with patch(
        "app.api.v1.endpoints.search.search_posts",
        new_callable=AsyncMock,
        return_value=([mock_result], 1),
    ):
        response = await client.get(
            "/api/v1/search",
            params={"q": "AI", "filter": "ai-ethics"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1


@pytest.mark.asyncio
async def test_search_with_date_sort(client: AsyncClient):
    """GET /search?q=AI&sort=date — 200, sorted by date."""
    mock_result = _make_mock_search_result()
    with patch(
        "app.api.v1.endpoints.search.search_posts",
        new_callable=AsyncMock,
        return_value=([mock_result], 1),
    ):
        response = await client.get(
            "/api/v1/search",
            params={"q": "AI", "sort": "date"},
        )
        assert response.status_code == 200


# ── Search (Error) ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_missing_query(client: AsyncClient):
    """GET /search — 422 when q parameter is missing."""
    response = await client.get("/api/v1/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_empty_query(client: AsyncClient):
    """GET /search?q= — 422 when q is empty string."""
    response = await client.get("/api/v1/search", params={"q": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_negative_skip(client: AsyncClient):
    """GET /search?q=AI&skip=-1 — 422 invalid pagination."""
    response = await client.get("/api/v1/search", params={"q": "AI", "skip": -1})
    assert response.status_code == 422


# ── Security: SQL Injection ────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_sql_injection(client: AsyncClient):
    """GET /search?q='; DROP TABLE posts;-- — treated literally, no crash."""
    with patch(
        "app.api.v1.endpoints.search.search_posts",
        new_callable=AsyncMock,
        return_value=([], 0),
    ):
        response = await client.get(
            "/api/v1/search",
            params={"q": "'; DROP TABLE posts; --"},
        )
        # Should return 200 with empty results, NOT 500
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_sqli_in_filter(client: AsyncClient):
    """GET /search?q=x&filter='; DROP TABLE categories;-- — treated literally."""
    with patch(
        "app.api.v1.endpoints.search.search_posts",
        new_callable=AsyncMock,
        return_value=([], 0),
    ):
        response = await client.get(
            "/api/v1/search",
            params={"q": "test", "filter": "'; DROP TABLE categories; --"},
        )
        assert response.status_code == 200


# ── Security: XSS ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_xss_in_query(client: AsyncClient):
    """GET /search?q=<script>alert('xss')</script> — no script reflection."""
    with patch(
        "app.api.v1.endpoints.search.search_posts",
        new_callable=AsyncMock,
        return_value=([], 0),
    ):
        response = await client.get(
            "/api/v1/search",
            params={"q": "<script>alert('xss')</script>"},
        )
        assert response.status_code == 200
        # Response must not reflect the script back
        assert "<script>" not in response.text


# ── Security: Oversized Query ──────────────────────────────────────

@pytest.mark.asyncio
async def test_search_oversized_query(client: AsyncClient):
    """GET /search?q=aaa...aaa — oversized query handled gracefully."""
    with patch(
        "app.api.v1.endpoints.search.search_posts",
        new_callable=AsyncMock,
        return_value=([], 0),
    ):
        response = await client.get(
            "/api/v1/search",
            params={"q": "a" * 5000},
        )
        # Should be handled, not crash
        assert response.status_code in (200, 422)


# ── Security: Response Data Leakage ────────────────────────────────

@pytest.mark.asyncio
async def test_search_response_no_sensitive_data(client: AsyncClient):
    """GET /search — results should not contain passwords or internal data."""
    mock_result = _make_mock_search_result()
    with patch(
        "app.api.v1.endpoints.search.search_posts",
        new_callable=AsyncMock,
        return_value=([mock_result], 1),
    ):
        response = await client.get("/api/v1/search", params={"q": "AI"})
        assert response.status_code == 200
        text = response.text.lower()
        assert "password" not in text
        assert "hashed" not in text
        assert "embedding" not in text
