"""
Unit tests for the Health API endpoint.

Covers:
  - Happy path (DB + Redis accessible)
  - Error path (DB failure, Redis failure)
  - Abuse path (method not allowed, no data leakage)
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.db.session import get_db
from app.core.redis import get_redis


# ── Helpers ─────────────────────────────────────────────────────────

def _mock_db_ok():
    """Yields a mock DB session where execute() succeeds."""
    async def _gen():
        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock())
        yield session
    return _gen


def _mock_db_fail():
    """Yields a mock DB session where execute() raises."""
    async def _gen():
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=Exception("DB down"))
        yield session
    return _gen


def _mock_redis_ok():
    """Yields a mock Redis client where ping() succeeds."""
    async def _gen():
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        yield client
    return _gen


def _mock_redis_fail():
    """Yields a mock Redis client where ping() raises."""
    async def _gen():
        client = AsyncMock()
        client.ping = AsyncMock(side_effect=Exception("Redis down"))
        yield client
    return _gen


# ── Happy Path ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check_all_ok(client: AsyncClient):
    """GET /health/ — 200, all statuses 'ok' when DB and Redis are accessible."""
    app.dependency_overrides[get_db] = _mock_db_ok()
    app.dependency_overrides[get_redis] = _mock_redis_ok()

    try:
        response = await client.get("/api/v1/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db_status"] == "ok"
        assert data["redis_status"] == "ok"
    finally:
        app.dependency_overrides.clear()


# ── Error Paths ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check_db_failure(client: AsyncClient):
    """GET /health/ — overall 'error' when DB is unreachable but Redis is up."""
    app.dependency_overrides[get_db] = _mock_db_fail()
    app.dependency_overrides[get_redis] = _mock_redis_ok()

    try:
        response = await client.get("/api/v1/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["db_status"] == "error"
        assert data["redis_status"] == "ok"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check_redis_failure(client: AsyncClient):
    """GET /health/ — overall 'error' when Redis is unreachable but DB is up."""
    app.dependency_overrides[get_db] = _mock_db_ok()
    app.dependency_overrides[get_redis] = _mock_redis_fail()

    try:
        response = await client.get("/api/v1/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["db_status"] == "ok"
        assert data["redis_status"] == "error"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check_both_failing(client: AsyncClient):
    """GET /health/ — overall 'error' when both DB and Redis are down."""
    app.dependency_overrides[get_db] = _mock_db_fail()
    app.dependency_overrides[get_redis] = _mock_redis_fail()

    try:
        response = await client.get("/api/v1/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["db_status"] == "error"
        assert data["redis_status"] == "error"
    finally:
        app.dependency_overrides.clear()


# ── Abuse Path ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check_method_not_allowed(client: AsyncClient):
    """POST /health/ — 405 Method Not Allowed."""
    response = await client.post("/api/v1/health/")
    assert response.status_code == 405


@pytest.mark.asyncio
async def test_health_check_response_no_sensitive_data(client: AsyncClient):
    """GET /health/ — response must never leak connection strings or internals."""
    app.dependency_overrides[get_db] = _mock_db_ok()
    app.dependency_overrides[get_redis] = _mock_redis_ok()

    try:
        response = await client.get("/api/v1/health/")
        assert response.status_code == 200
        text = response.text.lower()
        assert "password" not in text
        assert "postgres" not in text
        assert "connection" not in text
        assert "redis://localhost" not in text
    finally:
        app.dependency_overrides.clear()
