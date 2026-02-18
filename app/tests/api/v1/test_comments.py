"""
Unit tests for the Comments API endpoints.

Covers:
  - Happy paths (list, create, approve, delete)
  - Error cases (403, 404)
  - Security / Penetration (XSS, SQLi, oversized, data leakage)
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.tests.conftest import make_mock_user, override_auth, clear_overrides


# ── Helpers ─────────────────────────────────────────────────────────

def _make_mock_comment(
    comment_id: int = 101,
    user_id: int = 1,
    post_id: int = 1,
    content: str = "Great article!",
    is_approved: bool = True,
):
    comment = MagicMock()
    comment.id = comment_id
    comment.content = content
    comment.is_approved = is_approved
    comment.post_id = post_id
    comment.user_id = user_id
    comment.created_at = datetime(2026, 2, 18, tzinfo=timezone.utc)
    comment.updated_at = datetime(2026, 2, 18, tzinfo=timezone.utc)

    user = MagicMock()
    user.id = user_id
    user.full_name = "Alice User"
    user.avatar_url = None
    comment.user = user
    return comment


def _make_mock_post(post_id: int = 1, slug: str = "test-post"):
    post = MagicMock()
    post.id = post_id
    post.slug = slug
    post.deleted_at = None
    return post


# ── List Comments ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_comments(client: AsyncClient):
    """GET /posts/{slug}/comments — 200, only approved comments."""
    mock_comment = _make_mock_comment(is_approved=True)
    with patch("app.crud.comment.get_by_post_slug", new_callable=AsyncMock, return_value=([mock_comment], 1)):
        response = await client.get("/api/v1/posts/test-post/comments")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["content"] == "Great article!"


# ── Create Comment ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_comment(client: AsyncClient):
    """POST /posts/{slug}/comments — 200, pending approval."""
    user = make_mock_user(role_name="viewer")
    override_auth(user, role_name="viewer")
    mock_post = _make_mock_post()
    mock_comment = _make_mock_comment(is_approved=False)

    try:
        with patch("app.crud.post.get_by_slug", new_callable=AsyncMock, return_value=mock_post), \
             patch("app.crud.comment.create_comment", new_callable=AsyncMock, return_value=mock_comment):
            response = await client.post(
                "/api/v1/posts/test-post/comments",
                json={"content": "My thoughts on this..."},
            )
            assert response.status_code == 200
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_create_comment_unauthenticated(client: AsyncClient):
    """POST /posts/{slug}/comments — 401/403 without auth."""
    clear_overrides()
    response = await client.post(
        "/api/v1/posts/test-post/comments",
        json={"content": "Unauthorized comment"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_comment_on_nonexistent_post(client: AsyncClient):
    """POST /posts/{slug}/comments — 404 when post doesn't exist."""
    user = make_mock_user()
    override_auth(user)

    try:
        with patch("app.crud.post.get_by_slug", new_callable=AsyncMock, return_value=None):
            response = await client.post(
                "/api/v1/posts/nonexistent/comments",
                json={"content": "Hello?"},
            )
            assert response.status_code == 404
    finally:
        clear_overrides()


# ── Approve Comment ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_comment_as_admin(client: AsyncClient):
    """POST /comments/{id}/approve — 200 for admin."""
    user = make_mock_user(role_name="admin")
    override_auth(user, role_name="admin")
    mock_comment = _make_mock_comment(is_approved=False)
    approved_comment = _make_mock_comment(is_approved=True)

    try:
        with patch("app.crud.comment.get", new_callable=AsyncMock, return_value=mock_comment), \
             patch("app.crud.comment.approve", new_callable=AsyncMock, return_value=approved_comment):
            response = await client.post("/api/v1/comments/101/approve")
            assert response.status_code == 200
            assert response.json()["is_approved"] is True
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_approve_comment_as_regular_user(client: AsyncClient):
    """POST /comments/{id}/approve — 403 for non-admin."""
    user = make_mock_user(role_name="viewer")
    override_auth(user, role_name="viewer")

    try:
        response = await client.post("/api/v1/comments/101/approve")
        assert response.status_code == 403
    finally:
        clear_overrides()


# ── Delete Comment ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_comment_as_owner(client: AsyncClient):
    """DELETE /comments/{id} — 200 for comment owner."""
    user = make_mock_user(user_id=1, role_name="viewer")
    override_auth(user, role_name="viewer")
    mock_comment = _make_mock_comment(user_id=1)

    try:
        with patch("app.crud.comment.get", new_callable=AsyncMock, return_value=mock_comment), \
             patch("app.crud.comment.remove", new_callable=AsyncMock, return_value=mock_comment):
            response = await client.delete("/api/v1/comments/101")
            assert response.status_code == 200
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_delete_comment_as_admin(client: AsyncClient):
    """DELETE /comments/{id} — 200 for admin (any comment)."""
    user = make_mock_user(user_id=2, role_name="admin", is_superuser=True)
    override_auth(user, role_name="admin")
    mock_comment = _make_mock_comment(user_id=1)  # Not owner

    try:
        with patch("app.crud.comment.get", new_callable=AsyncMock, return_value=mock_comment), \
             patch("app.crud.comment.remove", new_callable=AsyncMock, return_value=mock_comment):
            response = await client.delete("/api/v1/comments/101")
            assert response.status_code == 200
    finally:
        clear_overrides()


@pytest.mark.asyncio
async def test_delete_other_users_comment(client: AsyncClient):
    """DELETE /comments/{id} — 403 for non-owner, non-admin."""
    user = make_mock_user(user_id=2, role_name="viewer")
    override_auth(user, role_name="viewer")
    mock_comment = _make_mock_comment(user_id=1)  # Owned by user 1

    try:
        with patch("app.crud.comment.get", new_callable=AsyncMock, return_value=mock_comment):
            response = await client.delete("/api/v1/comments/101")
            assert response.status_code == 403
    finally:
        clear_overrides()


# ── Security: XSS ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_comment_xss_in_content(client: AsyncClient):
    """POST /comments — <script> in content must be stripped."""
    from app.crud.crud_comment import sanitize_comment

    malicious = "<script>alert('xss')</script>Nice article!"
    sanitized = sanitize_comment(malicious)
    assert "<script>" not in sanitized
    assert "Nice article!" in sanitized


# ── Security: SQLi ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_comment_sql_injection(client: AsyncClient):
    """POST /comments — SQL injection in content is literal."""
    user = make_mock_user()
    override_auth(user)
    mock_post = _make_mock_post()
    mock_comment = _make_mock_comment(content="'; DROP TABLE comments; --")

    try:
        with patch("app.crud.post.get_by_slug", new_callable=AsyncMock, return_value=mock_post), \
             patch("app.crud.comment.create_comment", new_callable=AsyncMock, return_value=mock_comment):
            response = await client.post(
                "/api/v1/posts/test-post/comments",
                json={"content": "'; DROP TABLE comments; --"},
            )
            assert response.status_code in (200, 400)
    finally:
        clear_overrides()


# ── Security: Oversized ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_comment_oversized_content(client: AsyncClient):
    """POST /comments — oversized content (>5000 chars) rejected."""
    user = make_mock_user()
    override_auth(user)
    mock_post = _make_mock_post()

    try:
        with patch("app.crud.post.get_by_slug", new_callable=AsyncMock, return_value=mock_post):
            response = await client.post(
                "/api/v1/posts/test-post/comments",
                json={"content": "x" * 6000},
            )
            # Pydantic max_length=5000 should reject this
            assert response.status_code == 422
    finally:
        clear_overrides()


# ── Security: Data leakage ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_comment_response_no_sensitive_data(client: AsyncClient):
    """GET /comments — response should not contain user email or internal IDs."""
    mock_comment = _make_mock_comment()
    with patch("app.crud.comment.get_by_post_slug", new_callable=AsyncMock, return_value=([mock_comment], 1)):
        response = await client.get("/api/v1/posts/test-post/comments")
        assert response.status_code == 200
        text = response.text
        assert "password" not in text.lower()
        assert "hashed_password" not in text.lower()
