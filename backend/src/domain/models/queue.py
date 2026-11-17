from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.models.order import FulfillmentStatus


@dataclass(slots=True, kw_only=True)
class QueueProductInfo:
    id: UUID
    title: str
    slug: str
    image_url: str | None = None


@dataclass(slots=True, kw_only=True)
class QueueVariantInfo:
    id: UUID | None = None
    sku: str
    color: str | None = None
    size: str | None = None


@dataclass(slots=True, kw_only=True)
class QueueShippingAddress:
    city: str | None = None
    street: str | None = None
    postal_code: str | None = None


@dataclass(slots=True, kw_only=True)
class QueueCustomerInfo:
    id: UUID
    login: str
    email: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    phone_number: str | None = None


@dataclass(slots=True, kw_only=True)
class QueueItemDomain:
    id: UUID
    order_id: UUID
    created_at: datetime
    updated_at: datetime
    product: QueueProductInfo
    variant: QueueVariantInfo
    quantity: int
    unit_price: Decimal
    currency: str = "RUB"
    shipping_address: QueueShippingAddress
    customer: QueueCustomerInfo
    fulfillment_status: FulfillmentStatus = FulfillmentStatus.PENDING
    post_code: str | None = None
    tracking_url: str | None = None
