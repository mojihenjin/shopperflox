from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CartItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    quantity: int = Field(default=1, ge=1, le=100)


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    variant_id: UUID
    quantity: int
    product_id: UUID | None = None
    title: str | None = None
    sku: str | None = None
    size: str | None = None
    color_name: str | None = None
    unit_price: Decimal
    total_price: Decimal
    is_available: bool
    product_slug: str = ""
    image_url: str | None = None


class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    items: list[CartItemResponse]
    total_amount: Decimal
