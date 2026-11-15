from fastapi import APIRouter

from .auth import router as auth_router
from .cart import router as cart_router
from .categories import router as categories_router
from .favorites import router as favorites_router
from .moderation import router as moderation_router
from .orders import router as orders_router
from .payments import router as payments_router
from .products import router as products_router
from .reviews import router as reviews_router
from .search import router as search_router
from .users import router as users_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(users_router)
v1_router.include_router(moderation_router)
v1_router.include_router(categories_router)
v1_router.include_router(products_router)
v1_router.include_router(favorites_router)
v1_router.include_router(cart_router)
v1_router.include_router(orders_router)
v1_router.include_router(payments_router)
v1_router.include_router(reviews_router)
v1_router.include_router(search_router)

__all__ = [
    "auth_router",
    "cart_router",
    "categories_router",
    "favorites_router",
    "moderation_router",
    "orders_router",
    "payments_router",
    "products_router",
    "reviews_router",
    "search_router",
    "users_router",
    "v1_router",
]
