from decimal import Decimal
from typing import Protocol
from uuid import UUID

from src.domain.models import (
    CategoryDomain,
    FavoriteDomain,
    ProductDomain,
    ProductImageDomain,
    ProductVariantDomain,
)

from .uow import UnitOfWorkProtocol


class CategoryRepositoryProtocol(Protocol):
    async def get_by_id(self, category_id: UUID) -> CategoryDomain | None: ...

    async def get_by_slug(self, slug: str) -> CategoryDomain | None: ...

    async def list_all(self) -> list[CategoryDomain]: ...

    async def add(self, category: CategoryDomain) -> None: ...

    async def update(self, category: CategoryDomain) -> None: ...

    async def delete(self, category_id: UUID) -> None: ...


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
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProductDomain], int]: ...

    async def add(self, product: ProductDomain) -> None: ...

    async def update(self, product: ProductDomain) -> None: ...


class ProductVariantRepositoryProtocol(Protocol):
    async def get_by_id(self, variant_id: UUID) -> ProductVariantDomain | None: ...

    async def get_by_sku(self, sku: str) -> ProductVariantDomain | None: ...

    async def list_by_product_id(
        self, product_id: UUID
    ) -> list[ProductVariantDomain]: ...

    async def add(self, variant: ProductVariantDomain) -> None: ...

    async def update(self, variant: ProductVariantDomain) -> None: ...

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
