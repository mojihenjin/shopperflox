from fastapi import APIRouter

from .auth import router as auth_router
from .categories import router as categories_router
from .favorites import router as favorites_router
from .moderation import router as moderation_router
from .products import router as products_router
from .users import router as users_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(users_router)
v1_router.include_router(moderation_router)
v1_router.include_router(categories_router)
v1_router.include_router(products_router)
v1_router.include_router(favorites_router)

__all__ = [
    "auth_router",
    "categories_router",
    "favorites_router",
    "moderation_router",
    "products_router",
    "users_router",
    "v1_router",
]
