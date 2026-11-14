from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

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


@dataclass(slots=True, kw_only=True)
class OrderDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    user_id: UUID
    total_amount: Decimal
    shipping_address: dict
    created_by: UUID

    status: OrderStatus = field(default=OrderStatus.PENDING_PAYMENT)
    tracking_number: str | None = field(default=None)

    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)


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

