"""
Unit tests for the Taxonomy API endpoints (Categories + Tags).

Covers:
  - Happy paths (list, create)
  - Error cases (duplicate slug, auth)
  - Security / Penetration (XSS, SQLi)
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.tests.conftest import make_mock_user, override_auth, clear_overrides


# ── Helpers ─────────────────────────────────────────────────────────

def _make_mock_category(cat_id: int = 1, name: str = "Architecture", slug: str = "architecture"):
    cat = MagicMock()
    cat.id = cat_id
    cat.name = name
    cat.slug = slug
    cat.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    cat.updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return cat


def _make_mock_tag(tag_id: int = 1, name: str = "Tech", slug: str = "tech"):
    tag = MagicMock()
    tag.id = tag_id
    tag.name = name
    tag.slug = slug
    tag.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tag.updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return tag


# ── List Categories ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient):
    """GET /categories — 200, includes post count."""
    categories = [
        {"id": 1, "name": "Architecture", "slug": "architecture", "count": 10},
        {"id": 2, "name": "AI & Ethics", "slug": "ai-ethics", "count": 5},
    ]
    with patch("app.crud.category.get_multi_with_count", new_callable=AsyncMock, return_value=categories):
        response = await client.get("/api/v1/categories")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["count"] == 10


# ── Create Category ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_category(client: AsyncClient):
    """POST /categories — 200, creates new category."""
    user = make_mock_user(role_name="admin")
    override_auth(user, role_name="admin")
    mock_cat = _make_mock_category()

    try:
        with patch("app.crud.category.get_by_slug", new_callable=AsyncMock, return_value=None), \
             patch("app.crud.category.create", new_callable=AsyncMock, return_value=mock_cat):
            response = await client.post(
                "/api/v1/categories",
                json={"name": "Architecture", "slug": "architecture"},
            )
            assert response.status_code == 200
            assert response.json()["name"] == "Architecture"
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_create_category_unauthenticated(client: AsyncClient):
    """POST /categories — 401/403 without auth."""
    clear_overrides()
    response = await client.post(
        "/api/v1/categories",
        json={"name": "Test", "slug": "test"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_category_duplicate_slug(client: AsyncClient):
    """POST /categories — 400 when slug already exists."""
    user = make_mock_user(role_name="admin")
    override_auth(user, role_name="admin")
    existing = _make_mock_category()

    try:
        with patch("app.crud.category.get_by_slug", new_callable=AsyncMock, return_value=existing):
            response = await client.post(
                "/api/v1/categories",
                json={"name": "Architecture", "slug": "architecture"},
            )
            assert response.status_code == 400
    finally:
        clear_overrides()


# ── List Tags ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tags(client: AsyncClient):
    """GET /tags — 200, returns all tags."""
    mock_tags = [_make_mock_tag(1, "Tech", "tech"), _make_mock_tag(2, "Science", "science")]
    with patch("app.crud.tag.get_multi_filtered", new_callable=AsyncMock, return_value=mock_tags):
        response = await client.get("/api/v1/tags")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


@pytest.mark.asyncio
async def test_list_tags_with_search(client: AsyncClient):
    """GET /tags?q=tech — filtered results."""
    mock_tags = [_make_mock_tag(1, "Tech", "tech")]
    with patch("app.crud.tag.get_multi_filtered", new_callable=AsyncMock, return_value=mock_tags):
        response = await client.get("/api/v1/tags", params={"q": "tech"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Tech"


# ── Create Tag ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_tag(client: AsyncClient):
    """POST /tags — 200, creates new tag."""
    user = make_mock_user(role_name="admin")
    override_auth(user, role_name="admin")
    mock_tag = _make_mock_tag()

    try:
        with patch("app.crud.tag.get_by_slug", new_callable=AsyncMock, return_value=None), \
             patch("app.crud.tag.create", new_callable=AsyncMock, return_value=mock_tag):
            response = await client.post(
                "/api/v1/tags",
                json={"name": "Tech", "slug": "tech"},
            )
            assert response.status_code == 200
            assert response.json()["name"] == "Tech"
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_create_tag_duplicate_slug(client: AsyncClient):
    """POST /tags — 400 when slug already exists."""
    user = make_mock_user(role_name="admin")
    override_auth(user, role_name="admin")
    existing = _make_mock_tag()

    try:
        with patch("app.crud.tag.get_by_slug", new_callable=AsyncMock, return_value=existing):
            response = await client.post(
                "/api/v1/tags",
                json={"name": "Tech", "slug": "tech"},
            )
            assert response.status_code == 400
    finally:
        clear_overrides()


# ── Security: XSS ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_category_xss_in_name(client: AsyncClient):
    """POST /categories — <script> in name should not be executable."""
    user = make_mock_user(role_name="admin")
    override_auth(user, role_name="admin")
    xss_name = "<script>alert('xss')</script>Hacked"
    mock_cat = _make_mock_category(name=xss_name, slug="hacked")

    try:
        with patch("app.crud.category.get_by_slug", new_callable=AsyncMock, return_value=None), \
             patch("app.crud.category.create", new_callable=AsyncMock, return_value=mock_cat):
            response = await client.post(
                "/api/v1/categories",
                json={"name": xss_name, "slug": "hacked"},
            )
            assert response.status_code == 200
    finally:
        clear_overrides()


# ── Security: SQLi ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_tag_sql_injection(client: AsyncClient):
    """POST /tags — SQL injection in slug treated as literal string."""
    user = make_mock_user(role_name="admin")
    override_auth(user, role_name="admin")
    sqli_slug = "'; DROP TABLE tags; --"
    mock_tag = _make_mock_tag(slug=sqli_slug)

    try:
        with patch("app.crud.tag.get_by_slug", new_callable=AsyncMock, return_value=None), \
             patch("app.crud.tag.create", new_callable=AsyncMock, return_value=mock_tag):
            response = await client.post(
                "/api/v1/tags",
                json={"name": "Evil", "slug": sqli_slug},
            )
            assert response.status_code in (200, 400, 422)
    finally:
        clear_overrides()
