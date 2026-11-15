from fastapi import APIRouter

from .auth import router as auth_router
from .moderation import router as moderation_router
from .users import router as users_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(users_router)
v1_router.include_router(moderation_router)

__all__ = [
    "auth_router",
    "moderation_router",
    "users_router",
    "v1_router",
]
