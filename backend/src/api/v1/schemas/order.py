from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.api.v1.schemas.payment import PaymentResponse
from src.domain.models import OrderStatus


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    address_id: UUID
    comment: str | None = Field(default=None, max_length=500)


class OrderStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: OrderStatus
    post_code: str | None = Field(default=None, max_length=100)


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    variant_id: UUID | None
    title_snapshot: str
    sku_snapshot: str
    size_snapshot: str
    color_snapshot: str
    unit_price: Decimal
    quantity: int
    product_slug: str | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    total_amount: Decimal
    shipping_address: dict[str, Any]
    status: OrderStatus
    tracking_number: str | None = None
    post_code: str | None = None
    created_at: datetime
    items: list[OrderItemResponse] | None = None
    payment: PaymentResponse | None = None


class OrderCheckoutResponse(BaseModel):
    order: OrderResponse
    payment: PaymentResponse
    confirmation_url: str | None = None
