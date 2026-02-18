from pydantic import BaseModel


class HealthCheck(BaseModel):
    status: str
    db_status: str = "unknown"
    redis_status: str = "unknown"
