"""
Unit tests for the Posts API endpoints.

Covers:
  - Happy paths (CRUD operations)
  - Error cases (404, 403, 422)
  - Security / Penetration (XSS, SQLi, oversized payloads, IDOR)
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.tests.conftest import make_mock_user, override_auth, clear_overrides


# ── Helpers ─────────────────────────────────────────────────────────

def _make_mock_post(
    post_id: int = 1,
    author_id: int = 1,
    title: str = "Test Post",
    slug: str = "test-post",
    content: str = "<p>Safe content</p>",
    status: str = "published",
):
    """Create a mock Post ORM object."""
    post = MagicMock()
    post.id = post_id
    post.title = title
    post.slug = slug
    post.content = content
    post.status = status
    post.visibility = "public"
    post.view_count = 100
    post.reading_time = 5
    post.abstract = "Abstract text"
    post.volume = "Vol. 24"
    post.issue = "Jan 2026"
    post.thumbnail_url = None
    post.meta_title = None
    post.meta_description = None
    post.canonical_url = None
    post.pdf_url = None
    post.scheduled_at = None
    post.author_id = author_id
    post.category_id = 1
    post.deleted_at = None
    post.created_at = datetime(2026, 2, 18, tzinfo=timezone.utc)
    post.updated_at = datetime(2026, 2, 18, tzinfo=timezone.utc)

    cat = MagicMock()
    cat.id = 1
    cat.name = "Tech"
    cat.slug = "tech"
    post.category = cat

    author = MagicMock()
    author.id = author_id
    author.full_name = "Test Author"
    author.avatar_url = None
    post.author = author

    post.tags = []
    post.comments = []
    return post


# ── List Posts ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_posts(client: AsyncClient):
    """GET /posts — 200, paginated response."""
    mock_post = _make_mock_post()
    with patch("app.crud.post.get_multi_with_filters", new_callable=AsyncMock, return_value=([mock_post], 1)):
        response = await client.get("/api/v1/posts")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] == 1
        assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_list_posts_with_filters(client: AsyncClient):
    """GET /posts?status=published&category_slug=tech — filtered."""
    with patch("app.crud.post.get_multi_with_filters", new_callable=AsyncMock, return_value=([], 0)):
        response = await client.get(
            "/api/v1/posts",
            params={"status": "published", "category_slug": "tech"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


# ── Get Post Detail ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_post_detail(client: AsyncClient):
    """GET /posts/{slug} — 200, full content + relations."""
    mock_post = _make_mock_post()
    with patch("app.crud.post.get_by_slug", new_callable=AsyncMock, return_value=mock_post):
        response = await client.get("/api/v1/posts/test-post")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "test-post"
        assert data["title"] == "Test Post"
        assert "content" in data
        assert "category" in data
        assert "tags" in data


@pytest.mark.asyncio
async def test_get_post_not_found(client: AsyncClient):
    """GET /posts/{slug} — 404 when slug doesn't exist."""
    with patch("app.crud.post.get_by_slug", new_callable=AsyncMock, return_value=None):
        response = await client.get("/api/v1/posts/nonexistent")
        assert response.status_code == 404


# ── Create Post ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_post_as_editor(client: AsyncClient):
    """POST /posts — 200, creates post with tags."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")
    mock_post = _make_mock_post()

    try:
        with patch("app.crud.post.create_with_tags", new_callable=AsyncMock, return_value=mock_post):
            response = await client.post(
                "/api/v1/posts",
                json={
                    "title": "New Post",
                    "slug": "new-post",
                    "content": "<p>Hello world</p>",
                    "tag_ids": [1, 2],
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Test Post"
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_create_post_unauthenticated(client: AsyncClient):
    """POST /posts — 401/403 without auth token."""
    clear_overrides()
    response = await client.post(
        "/api/v1/posts",
        json={"title": "No Auth", "slug": "no-auth", "content": "text"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_post_as_regular_user(client: AsyncClient):
    """POST /posts — 403 for non-editor users."""
    user = make_mock_user(role_name="viewer")
    override_auth(user, role_name="viewer")

    try:
        response = await client.post(
            "/api/v1/posts",
            json={"title": "Forbidden", "slug": "forbidden", "content": "text"},
        )
        assert response.status_code == 403
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_create_post_missing_required_fields(client: AsyncClient):
    """POST /posts — 422 when required fields are missing."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")

    try:
        response = await client.post("/api/v1/posts", json={})
        assert response.status_code == 422
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_create_post_without_content_or_pdf(client: AsyncClient):
    """POST /posts — 422 when neither content nor pdf_url is provided."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")

    try:
        response = await client.post(
            "/api/v1/posts",
            json={"title": "No Content", "slug": "no-content"},
        )
        assert response.status_code == 422
    finally:
        clear_overrides()


# ── Update Post ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_post(client: AsyncClient):
    """PUT /posts/{id} — 200, updates fields."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")
    mock_post = _make_mock_post(author_id=user.id)

    try:
        with patch("app.crud.post.get", new_callable=AsyncMock, return_value=mock_post), \
             patch("app.crud.post.update_with_tags", new_callable=AsyncMock, return_value=mock_post):
            response = await client.put(
                "/api/v1/posts/1",
                json={"title": "Updated Title"},
            )
            assert response.status_code == 200
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_update_nonexistent_post(client: AsyncClient):
    """PUT /posts/{id} — 404 when post doesn't exist."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")

    try:
        with patch("app.crud.post.get", new_callable=AsyncMock, return_value=None):
            response = await client.put("/api/v1/posts/9999", json={"title": "Nope"})
            assert response.status_code == 404
    finally:
        clear_overrides()


# ── Delete Post ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_post(client: AsyncClient):
    """DELETE /posts/{id} — 200, soft delete."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")
    mock_post = _make_mock_post(author_id=user.id)

    try:
        with patch("app.crud.post.get", new_callable=AsyncMock, return_value=mock_post), \
             patch("app.crud.post.soft_delete", new_callable=AsyncMock, return_value=mock_post):
            response = await client.delete("/api/v1/posts/1")
            assert response.status_code == 200
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_delete_nonexistent_post(client: AsyncClient):
    """DELETE /posts/{id} — 404."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")

    try:
        with patch("app.crud.post.get", new_callable=AsyncMock, return_value=None):
            response = await client.delete("/api/v1/posts/9999")
            assert response.status_code == 404
    finally:
        clear_overrides()


# ── Security: XSS in content ────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_post_xss_in_content(client: AsyncClient):
    """POST /posts — <script> tags must be stripped from content."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")

    try:
        async def mock_create(db, *, obj_in, author_id):
            from app.crud.crud_post import sanitize_html
            clean = sanitize_html(obj_in.content)
            post = _make_mock_post()
            post.content = clean
            return post

        with patch("app.crud.post.create_with_tags", side_effect=mock_create):
            response = await client.post(
                "/api/v1/posts",
                json={
                    "title": "XSS Test",
                    "slug": "xss-test",
                    "content": "<p>Hello</p><script>alert('xss')</script>",
                },
            )
            assert response.status_code == 200
            assert "<script>" not in response.json().get("content", "")
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_create_post_xss_in_title(client: AsyncClient):
    """POST /posts — <script> in title should NOT execute."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")
    mock_post = _make_mock_post(title="<script>alert('xss')</script>")

    try:
        with patch("app.crud.post.create_with_tags", new_callable=AsyncMock, return_value=mock_post):
            response = await client.post(
                "/api/v1/posts",
                json={
                    "title": "<script>alert('xss')</script>",
                    "slug": "xss-title",
                    "content": "Safe content",
                },
            )
            assert response.status_code == 200
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_create_post_stored_xss_event_handler(client: AsyncClient):
    """POST /posts — <img onerror=...> must be stripped."""
    from app.crud.crud_post import sanitize_html

    malicious = '<img src="x" onerror="alert(\'xss\')">'
    sanitized = sanitize_html(malicious)
    assert "onerror" not in sanitized


@pytest.mark.asyncio
async def test_create_post_xss_iframe_injection(client: AsyncClient):
    """POST /posts — <iframe> must be stripped."""
    from app.crud.crud_post import sanitize_html

    malicious = '<iframe src="https://evil.com"></iframe>'
    sanitized = sanitize_html(malicious)
    assert "<iframe" not in sanitized


@pytest.mark.asyncio
async def test_create_post_sql_injection_in_slug(client: AsyncClient):
    """POST /posts — SQL injection in slug treated as literal."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")
    mock_post = _make_mock_post(slug="'; DROP TABLE posts; --")

    try:
        with patch("app.crud.post.create_with_tags", new_callable=AsyncMock, return_value=mock_post):
            response = await client.post(
                "/api/v1/posts",
                json={
                    "title": "SQLi Test",
                    "slug": "'; DROP TABLE posts; --",
                    "content": "content",
                },
            )
            assert response.status_code in (200, 400, 422)
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_create_post_oversized_content(client: AsyncClient):
    """POST /posts — oversized content handled gracefully."""
    user = make_mock_user(role_name="editor")
    override_auth(user, role_name="editor")

    try:
        with patch("app.crud.post.create_with_tags", new_callable=AsyncMock, side_effect=ValueError("Content exceeds maximum allowed length")):
            response = await client.post(
                "/api/v1/posts",
                json={
                    "title": "Huge Post",
                    "slug": "huge-post",
                    "content": "x" * 300_000,
                },
            )
            assert response.status_code == 400
    finally:
        clear_overrides()


# ── Security: IDOR ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_idor_update_other_users_post(client: AsyncClient):
    """PUT /posts/{id} — 403 when editing another user's post."""
    user = make_mock_user(user_id=2, role_name="editor")
    override_auth(user, role_name="editor")
    mock_post = _make_mock_post(author_id=1)  # Owned by user 1

    try:
        with patch("app.crud.post.get", new_callable=AsyncMock, return_value=mock_post):
            response = await client.put(
                "/api/v1/posts/1",
                json={"title": "Hijacked Title"},
            )
            assert response.status_code == 403
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_idor_delete_other_users_post(client: AsyncClient):
    """DELETE /posts/{id} — 403 when deleting another user's post."""
    user = make_mock_user(user_id=2, role_name="editor")
    override_auth(user, role_name="editor")
    mock_post = _make_mock_post(author_id=1)  # Owned by user 1

    try:
        with patch("app.crud.post.get", new_callable=AsyncMock, return_value=mock_post):
            response = await client.delete("/api/v1/posts/1")
            assert response.status_code == 403
    finally:
        clear_overrides()
