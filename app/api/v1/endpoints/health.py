from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api import dependencies as deps
from app.schemas.health import HealthCheck

router = APIRouter()

@router.get("/", response_model=HealthCheck, status_code=status.HTTP_200_OK)
async def health_check(
    db: AsyncSession = Depends(deps.get_db),
) -> HealthCheck:
    """
    Check if the service is up and the database is accessible.
    """
    try:
        # Simple query to check DB connection
        await db.execute(text("SELECT 1"))
        return HealthCheck(status="ok")
    except Exception as e:
        # Log error in production
        print(f"Health check failed: {e}")
        return HealthCheck(status="error")
