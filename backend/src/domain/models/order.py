from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from src.domain.exceptions import DomainValidationError, InvalidStateTransitionError
from src.utils import factory_now
from uuid6 import uuid7

from .base import BaseDomain


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


ALLOWED_ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING_PAYMENT: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {
        OrderStatus.PROCESSING,
        OrderStatus.CANCELLED,
        OrderStatus.REFUNDED,
    },
    OrderStatus.PROCESSING: {
        OrderStatus.SHIPPED,
        OrderStatus.CANCELLED,
        OrderStatus.REFUNDED,
    },
    OrderStatus.SHIPPED: {
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
        OrderStatus.REFUNDED,
    },
    OrderStatus.DELIVERED: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUNDED: set(),
}


@dataclass(slots=True, kw_only=True)
class OrderDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    user_id: UUID
    total_amount: Decimal
    shipping_address: dict[str, Any]
    created_by: UUID

    status: OrderStatus = field(default=OrderStatus.PENDING_PAYMENT)
    tracking_number: str | None = field(default=None)

    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)

    def __post_init__(self) -> None:
        if self.total_amount < 0:
            raise DomainValidationError("Order total_amount must be non-negative")

    def transition_to(self, new_status: OrderStatus) -> None:
        allowed = ALLOWED_ORDER_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition order from {self.status} to {new_status}"
            )
        self.status = new_status
        self.updated_at = factory_now()


@dataclass(slots=True, kw_only=True)
class OrderItemDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    order_id: UUID
    title_snapshot: str
    sku_snapshot: str
    size_snapshot: str
    color_snapshot: str
    unit_price: Decimal
    quantity: int
    created_by: UUID

    variant_id: UUID | None = field(default=None)
    created_at: datetime = field(default_factory=factory_now)

    def __post_init__(self) -> None:
        if self.unit_price < 0:
            raise DomainValidationError("OrderItem unit_price must be non-negative")
        if self.quantity <= 0:
            raise DomainValidationError("OrderItem quantity must be greater than zero")
