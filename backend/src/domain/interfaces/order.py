from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from src.domain.interfaces.brand import BrandRepositoryProtocol
from src.domain.interfaces.cart import CartRepositoryProtocol
from src.domain.interfaces.catalog import (
    ProductRepositoryProtocol,
    ProductVariantRepositoryProtocol,
)
from src.domain.interfaces.user import UserAddressRepositoryProtocol
from src.domain.models import (
    OrderDomain,
    OrderItemDomain,
    OrderStatus,
    PaymentDomain,
    ReviewDomain,
)


class OrderRepositoryProtocol(Protocol):
    async def get_by_id(
        self, order_id: UUID, *, for_update: bool = False
    ) -> OrderDomain | None: ...

    async def list_items(self, order_id: UUID) -> list[OrderItemDomain]: ...

    async def list_by_user_id(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[OrderDomain], int]: ...

    async def list_all(
        self,
        status: OrderStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[OrderDomain], int]: ...

    async def has_user_purchased_product(
        self, user_id: UUID, product_id: UUID
    ) -> bool: ...

    async def add(
        self, order: OrderDomain, items: list[OrderItemDomain] | None = None
    ) -> None: ...

    async def update(self, order: OrderDomain) -> None: ...


class PaymentRepositoryProtocol(Protocol):
    async def get_by_id(
        self, payment_id: UUID, *, for_update: bool = False
    ) -> PaymentDomain | None: ...

    async def get_by_order_id(
        self, order_id: UUID, *, for_update: bool = False
    ) -> PaymentDomain | None: ...

    async def get_by_external_id(
        self, external_transaction_id: str, *, for_update: bool = False
    ) -> PaymentDomain | None: ...

    async def add(self, payment: PaymentDomain) -> None: ...

    async def update(self, payment: PaymentDomain) -> None: ...


class ReviewRepositoryProtocol(Protocol):
    async def get_by_id(self, review_id: UUID) -> ReviewDomain | None: ...

    async def get_by_user_and_product(
        self, user_id: UUID, product_id: UUID
    ) -> ReviewDomain | None: ...

    async def list_by_product_id(
        self, product_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[ReviewDomain], int]: ...

    async def add(self, review: ReviewDomain) -> None: ...

    async def delete(self, review_id: UUID) -> None: ...


class OrderUnitOfWorkProtocol(Protocol):
    orders: OrderRepositoryProtocol
    carts: CartRepositoryProtocol
    variants: ProductVariantRepositoryProtocol
    products: ProductRepositoryProtocol
    addresses: UserAddressRepositoryProtocol
    payments: PaymentRepositoryProtocol
    brands: BrandRepositoryProtocol

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...


class ReviewUnitOfWorkProtocol(Protocol):
    reviews: ReviewRepositoryProtocol
    orders: OrderRepositoryProtocol
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
