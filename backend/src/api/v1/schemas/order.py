from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.api.v1.schemas.payment import PaymentResponse
from src.domain.models import OrderStatus


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    recipient_firstname: str = Field(default="")
    recipient_lastname: str = Field(default="")
    recipient_middlename: str | None = Field(default=None)
    save_to_profile: bool = Field(default=False)
    passport_series: str = Field(default="")
    passport_number: str = Field(default="")
    delivery_type: Literal["address", "post_office"] = Field(default="address")

    # Address fields
    country: str = Field(default="Россия", max_length=128)
    region: str | None = Field(default=None, max_length=128)
    city: str = Field(default="", max_length=128)
    house: str = Field(default="", max_length=64)
    apartment: str | None = Field(default=None, max_length=64)
    postal_code: str = Field(default="", max_length=32)
    save_address_to_profile: bool = Field(default=False)

    # Post office field
    post_office_id: UUID | None = Field(default=None)

    # Legacy backward compatibility
    address_id: UUID | None = Field(default=None)
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_checkout_fields(self) -> Self:
        if self.address_id is not None:
            return self

        if not self.recipient_firstname:
            raise ValueError("Имя получателя (recipient_firstname) обязательно")
        if not self.recipient_lastname:
            raise ValueError("Фамилия получателя (recipient_lastname) обязательно")

        if (
            not self.passport_series
            or len(self.passport_series) != 4
            or not self.passport_series.isdigit()
        ):
            raise ValueError("Серия паспорта должна состоять ровно из 4 цифр")
        if (
            not self.passport_number
            or len(self.passport_number) != 6
            or not self.passport_number.isdigit()
        ):
            raise ValueError("Номер паспорта должен состоять ровно из 6 цифр")

        if self.delivery_type == "address":
            if not self.city:
                raise ValueError("Город (city) обязателен для доставки по адресу")
            if not self.house:
                raise ValueError("Дом (house) обязателен для доставки по адресу")
            if not self.postal_code:
                raise ValueError(
                    "Почтовый индекс (postal_code) обязателен для доставки по адресу"
                )
        elif self.delivery_type == "post_office":
            if not self.post_office_id:
                raise ValueError(
                    "post_office_id обязателен для доставки в почтовое отделение"
                )

        return self


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
    recipient_firstname: str = ""
    recipient_lastname: str = ""
    recipient_middlename: str | None = None
    passport_series: str | None = None
    passport_number: str | None = None
    delivery_type: str = "address"
    post_office_id: UUID | None = None
    shipping_country: str = "Россия"
    shipping_region: str | None = None
    shipping_city: str = ""
    shipping_house: str = ""
    shipping_apartment: str | None = None
    shipping_postal_code: str = ""
    is_paid: bool = False
    paid_at: datetime | None = None
    created_at: datetime
    items: list[OrderItemResponse] | None = None
    payment: PaymentResponse | None = None


class OrderCheckoutResponse(BaseModel):
    order: OrderResponse
    payment: PaymentResponse | None = None
    confirmation_url: str | None = None
    payment_mode: Literal["billing", "debug", "unavailable"] | str = "unavailable"
    payment_url: str | None = None
