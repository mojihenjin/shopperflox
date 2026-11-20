from decimal import Decimal
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from src.domain.models import (
    BrandSearchResult,
    CategoryDomain,
    FavoriteDomain,
    ProductDomain,
    ProductImageDomain,
    ProductVariantDomain,
)

from .uow import UnitOfWorkProtocol

if TYPE_CHECKING:
    from .brand import BrandRepositoryProtocol


class CategoryRepositoryProtocol(Protocol):
    async def get_by_id(self, category_id: UUID) -> CategoryDomain | None: ...

    async def get_by_slug(self, slug: str) -> CategoryDomain | None: ...

    async def list_all(self) -> list[CategoryDomain]: ...

    async def add(self, category: CategoryDomain) -> None: ...

    async def update(self, category: CategoryDomain) -> None: ...

    async def delete(self, category_id: UUID) -> None: ...

    async def list_admin(
        self,
        *,
        search: str | None = None,
        sort_by: str = "sort_order",
        sort_order: str = "asc",
    ) -> list[CategoryDomain]: ...


class ProductRepositoryProtocol(Protocol):
    async def get_by_id(
        self, product_id: UUID, *, include_unpublished: bool = False
    ) -> ProductDomain | None: ...

    async def get_by_slug(
        self, slug: str, *, include_unpublished: bool = False
    ) -> ProductDomain | None: ...

    async def list_catalog(
        self,
        *,
        category_id: UUID | None = None,
        brand_id: UUID | None = None,
        brand_slug: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        search: str | None = None,
        size: str | None = None,
        color: str | None = None,
        is_limited: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductDomain], int]: ...

    async def list_self_worked_by_creator(
        self, creator_id: UUID
    ) -> list[ProductDomain]: ...

    async def increment_views(self, product_id: UUID) -> None: ...

    async def increment_orders(self, product_id: UUID, quantity: int) -> None: ...

    async def add(self, product: ProductDomain) -> None: ...

    async def update(self, product: ProductDomain) -> None: ...

    async def search_products(
        self, query: str, limit: int = 10
    ) -> list[ProductDomain]: ...

    async def search_brands(
        self, query: str, limit: int = 10
    ) -> list[BrandSearchResult]: ...

    async def update_brand_name_for_products(
        self, brand_id: UUID, brand_name: str
    ) -> None: ...

    async def list_pending_products(
        self,
        *,
        request_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductDomain], int]: ...

    async def count_pending_products(self) -> int: ...

    async def count_by_category_id(self, category_id: UUID) -> int: ...

    async def hide_all_by_brand_id(self, brand_id: UUID) -> int: ...

    async def list_admin(
        self,
        *,
        search: str | None = None,
        moderation_status: str | None = None,
        is_hidden: int | None = None,
        is_limited: bool | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductDomain], int]: ...


class ProductVariantRepositoryProtocol(Protocol):
    async def get_by_id(self, variant_id: UUID) -> ProductVariantDomain | None: ...

    async def get_by_sku(self, sku: str) -> ProductVariantDomain | None: ...

    async def get_by_ids_for_update(
        self, variant_ids: list[UUID]
    ) -> list[ProductVariantDomain]: ...

    async def list_by_product_id(
        self, product_id: UUID
    ) -> list[ProductVariantDomain]: ...

    async def search_variants(
        self, query: str, limit: int = 10
    ) -> list[ProductVariantDomain]: ...

    async def add(self, variant: ProductVariantDomain) -> None: ...

    async def update(self, variant: ProductVariantDomain) -> None: ...

    async def increment_orders(self, variant_id: UUID, quantity: int) -> None: ...

    async def delete(self, variant_id: UUID) -> None: ...


class ProductImageRepositoryProtocol(Protocol):
    async def get_by_id(self, image_id: UUID) -> ProductImageDomain | None: ...

    async def list_by_product_id(
        self, product_id: UUID
    ) -> list[ProductImageDomain]: ...

    async def unset_main_for_product(self, product_id: UUID) -> None: ...

    async def add(self, image: ProductImageDomain) -> None: ...

    async def update(self, image: ProductImageDomain) -> None: ...

    async def delete(self, image_id: UUID) -> None: ...


class FavoriteRepositoryProtocol(Protocol):
    async def exists(self, user_id: UUID, product_id: UUID) -> bool: ...

    async def list_user_favorite_products(
        self, user_id: UUID, *, limit: int = 20, offset: int = 0
    ) -> tuple[list[ProductDomain], int]: ...

    async def add(self, favorite: FavoriteDomain) -> None: ...

    async def delete(self, user_id: UUID, product_id: UUID) -> None: ...


class CatalogUnitOfWorkProtocol(UnitOfWorkProtocol, Protocol):
    categories: CategoryRepositoryProtocol
    products: ProductRepositoryProtocol
    variants: ProductVariantRepositoryProtocol
    images: ProductImageRepositoryProtocol
    favorites: FavoriteRepositoryProtocol
    brands: "BrandRepositoryProtocol"
