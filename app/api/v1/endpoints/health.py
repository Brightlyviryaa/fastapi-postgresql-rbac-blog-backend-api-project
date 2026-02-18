from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import dependencies as deps
from app.core.redis import get_redis
from app.schemas.health import HealthCheck

router = APIRouter()


@router.get("/", response_model=HealthCheck, status_code=status.HTTP_200_OK)
async def health_check(
    db: AsyncSession = Depends(deps.get_db),
    redis: Redis = Depends(get_redis),
) -> HealthCheck:
    """
    Check if the service is up and core dependencies (DB, Redis) are accessible.
    """
    db_status = "ok"
    redis_status = "ok"

    # ── Database ──
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # ── Redis ──
    try:
        await redis.ping()
    except Exception:
        redis_status = "error"

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "error"

    return HealthCheck(
        status=overall,
        db_status=db_status,
        redis_status=redis_status,
    )
