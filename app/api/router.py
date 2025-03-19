from fastapi import APIRouter

from app.api.routes import assets, creations, health, shares, threads
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(threads.router, prefix=f"{settings.api_v1_prefix}/threads", tags=["threads"])
api_router.include_router(creations.router, prefix=settings.api_v1_prefix, tags=["creations"])
api_router.include_router(shares.router, prefix=settings.api_v1_prefix, tags=["shares"])
api_router.include_router(assets.router, prefix=settings.api_v1_prefix, tags=["assets"])
