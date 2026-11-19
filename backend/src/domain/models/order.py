from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from uuid6 import uuid7

from src.domain.exceptions import DomainValidationError, InvalidStateTransitionError
from src.utils import factory_now

from .base import BaseDomain


class OrderStatus(StrEnum):
    AWAITING_PAYMENT = "awaiting_payment"
    PENDING = "pending"
    PACKING = "packing"
    HANDED_TO_POST = "handed_to_post"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    RETURNING = "returning"
    RETURNED = "returned"
    CANCELLED = "cancelled"

    # Backward compatibility
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    REFUNDED = "refunded"


class FulfillmentStatus(StrEnum):
    AWAITING_PAYMENT = "awaiting_payment"
    PENDING = "pending"
    PACKING = "packing"
    HANDED_TO_POST = "handed_to_post"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    RETURNING = "returning"
    RETURNED = "returned"
    CANCELLED = "cancelled"


ALLOWED_ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.AWAITING_PAYMENT: {
        OrderStatus.PENDING,
        OrderStatus.PAID,
        OrderStatus.PACKING,
        OrderStatus.CANCELLED,
    },
    OrderStatus.PENDING_PAYMENT: {
        OrderStatus.PENDING,
        OrderStatus.PAID,
        OrderStatus.PACKING,
        OrderStatus.CANCELLED,
    },
    OrderStatus.PAID: {
        OrderStatus.PENDING,
        OrderStatus.PACKING,
        OrderStatus.PROCESSING,
        OrderStatus.CANCELLED,
        OrderStatus.REFUNDED,
    },
    OrderStatus.PENDING: {
        OrderStatus.PACKING,
        OrderStatus.HANDED_TO_POST,
        OrderStatus.IN_TRANSIT,
        OrderStatus.CANCELLED,
        OrderStatus.RETURNING,
    },
    OrderStatus.PROCESSING: {
        OrderStatus.PACKING,
        OrderStatus.HANDED_TO_POST,
        OrderStatus.IN_TRANSIT,
        OrderStatus.SHIPPED,
        OrderStatus.CANCELLED,
        OrderStatus.REFUNDED,
    },
    OrderStatus.PACKING: {
        OrderStatus.HANDED_TO_POST,
        OrderStatus.IN_TRANSIT,
        OrderStatus.CANCELLED,
        OrderStatus.RETURNING,
    },
    OrderStatus.HANDED_TO_POST: {
        OrderStatus.IN_TRANSIT,
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
        OrderStatus.RETURNING,
    },
    OrderStatus.SHIPPED: {
        OrderStatus.IN_TRANSIT,
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
        OrderStatus.RETURNING,
        OrderStatus.REFUNDED,
    },
    OrderStatus.IN_TRANSIT: {
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
        OrderStatus.RETURNING,
    },
    OrderStatus.DELIVERED: {
        OrderStatus.RETURNING,
        OrderStatus.RETURNED,
        OrderStatus.REFUNDED,
    },
    OrderStatus.RETURNING: {
        OrderStatus.RETURNED,
        OrderStatus.DELIVERED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.RETURNED: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUNDED: set(),
}


@dataclass(slots=True, kw_only=True)
class OrderDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    user_id: UUID
    total_amount: Decimal
    shipping_address: dict[str, Any] = field(default_factory=dict)
    created_by: UUID

    status: OrderStatus = field(default=OrderStatus.AWAITING_PAYMENT)
    tracking_number: str | None = field(default=None)
    post_code: str | None = field(default=None)

    # Recipient
    recipient_firstname: str = field(default="")
    recipient_lastname: str = field(default="")
    recipient_middlename: str | None = field(default=None)

    # Passport (stored strictly in order, cleared on delivered/returned)
    passport_series: str | None = field(default=None)
    passport_number: str | None = field(default=None)

    # Delivery & shipping
    delivery_type: Literal["address", "post_office"] = field(default="address")
    post_office_id: UUID | None = field(default=None)
    shipping_country: str = field(default="Россия")
    shipping_region: str | None = field(default=None)
    shipping_city: str = field(default="")
    shipping_house: str = field(default="")
    shipping_apartment: str | None = field(default=None)
    shipping_postal_code: str = field(default="")

    # Payment
    is_paid: bool = field(default=False)
    paid_at: datetime | None = field(default=None)
    currency: str = field(default="RUB")

    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)

    def __post_init__(self) -> None:
        if self.total_amount < 0:
            raise DomainValidationError("Order total_amount must be non-negative")
        if isinstance(self.status, str):
            self.status = OrderStatus(self.status)

    def transition_to(self, new_status: OrderStatus) -> None:
        if self.status == new_status:
            return
        allowed = ALLOWED_ORDER_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition order from {self.status} to {new_status}"
            )
        self.status = new_status
        if new_status in {OrderStatus.DELIVERED, OrderStatus.RETURNED}:
            self.passport_series = None
            self.passport_number = None
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
    product_slug: str | None = field(default=None)
    fulfillment_status: FulfillmentStatus = field(default=FulfillmentStatus.PENDING)
    post_code: str | None = field(default=None)
    tracking_url: str | None = field(default=None)
    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)

    def __post_init__(self) -> None:
        if self.unit_price < 0:
            raise DomainValidationError("OrderItem unit_price must be non-negative")
        if self.quantity <= 0:
            raise DomainValidationError("OrderItem quantity must be greater than zero")
        if isinstance(self.fulfillment_status, str):
            self.fulfillment_status = FulfillmentStatus(self.fulfillment_status)
