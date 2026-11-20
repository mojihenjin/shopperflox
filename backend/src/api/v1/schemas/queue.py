from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.models import FulfillmentStatus

from .common import SafeUrl


class QueueProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    image_url: str | None = None


class QueueVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    sku: str
    color: str | None = None
    size: str | None = None


class QueueShippingAddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    city: str | None = None
    street: str | None = None
    postal_code: str | None = None


class QueueCustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    login: str
    email: str | None = None
    firstname: str | None = None
    lastname: str | None = None
    phone_number: str | None = None


class QueueItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    created_at: datetime
    updated_at: datetime
    product: QueueProductResponse
    variant: QueueVariantResponse
    quantity: int
    unit_price: Decimal
    currency: str = "RUB"
    shipping_address: QueueShippingAddressResponse
    customer: QueueCustomerResponse
    fulfillment_status: FulfillmentStatus
    post_code: str | None = None
    tracking_url: str | None = None


class QueueItemUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    fulfillment_status: FulfillmentStatus | None = None
    post_code: str | None = Field(default=None, max_length=100)
    tracking_url: SafeUrl | None = Field(default=None, max_length=512)
