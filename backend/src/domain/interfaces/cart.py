from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from src.domain.interfaces.catalog import (
    ProductRepositoryProtocol,
    ProductVariantRepositoryProtocol,
)
from src.domain.models import CartDomain, CartItemDomain


class CartRepositoryProtocol(Protocol):
    async def get_by_user_id(self, user_id: UUID) -> CartDomain | None: ...

    async def get_or_create_for_user(self, user_id: UUID) -> CartDomain: ...

    async def list_items(self, cart_id: UUID) -> list[CartItemDomain]: ...

    async def get_item(
        self, cart_id: UUID, variant_id: UUID
    ) -> CartItemDomain | None: ...

    async def upsert_item(
        self, cart_id: UUID, variant_id: UUID, quantity: int
    ) -> CartItemDomain: ...

    async def remove_item(self, cart_id: UUID, variant_id: UUID) -> None: ...

    async def clear_cart(self, cart_id: UUID) -> None: ...


class CartUnitOfWorkProtocol(Protocol):
    carts: CartRepositoryProtocol
    variants: ProductVariantRepositoryProtocol
    products: ProductRepositoryProtocol

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...
