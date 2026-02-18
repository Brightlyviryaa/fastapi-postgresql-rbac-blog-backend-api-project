from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    comments,
    dashboard,
    health,
    posts,
    search,
    subscribers,
    taxonomy,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(posts.router, tags=["posts"])
api_router.include_router(comments.router, tags=["comments"])
api_router.include_router(taxonomy.router, tags=["taxonomy"])
api_router.include_router(subscribers.router, tags=["subscribers"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(search.router, tags=["search"])
