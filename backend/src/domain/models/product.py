from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from uuid6 import uuid7

from src.domain.exceptions import DomainValidationError
from src.utils import factory_now

from .base import BaseDomain


class ModerationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ModerationRequestType(StrEnum):
    CREATE = "CREATE"
    EDIT = "EDIT"


@dataclass(slots=True, kw_only=True)
class ProductDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    category_id: UUID
    title: str
    slug: str
    base_price: Decimal
    created_by: UUID

    creator_id: UUID | None = field(default=None)
    description: str | None = field(default=None)
    brand_id: UUID | None = field(default=None)
    brand: str | None = field(default=None)
    brand_slug: str | None = field(default=None)
    brand_logo_url: str | None = field(default=None)
    brand_his_url: str | None = field(default=None)
    brand_is_verified: bool = field(default=False)
    brand_is_deleted: bool = field(default=False)
    brand_products_hidden_override: int | None = field(default=None)
    is_self_worked: bool = field(default=False)
    price_usd: Decimal | None = field(default=None)
    price_eur: Decimal | None = field(default=None)
    price_cny: Decimal | None = field(default=None)
    creator_login: str | None = field(default=None)
    creator_verified: bool = field(default=False)

    material: str | None = field(default=None)
    density: str | None = field(default=None)
    composition: str | None = field(default=None)
    print_method: str | None = field(default=None)
    note: str | None = field(default=None)

    attributes: dict[str, Any] = field(default_factory=dict)
    is_published: bool = field(default=False)
    is_hidden: int = field(default=0)
    effective_hidden: int = field(default=0)
    is_limited: bool = field(default=False)
    views_count: int = field(default=0)
    orders_count: int = field(default=0)

    images: list["ProductImageDomain"] = field(default_factory=list)
    variants: list["ProductVariantDomain"] = field(default_factory=list)

    moderation_status: ModerationStatus = field(default=ModerationStatus.PENDING)
    request_type: ModerationRequestType = field(default=ModerationRequestType.CREATE)
    rejection_reason: str | None = field(default=None)

    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)
    deleted_at: datetime | None = field(default=None)

    def __post_init__(self) -> None:
        if self.base_price < 0:
            raise DomainValidationError("Product base_price must be non-negative")
        if self.price_usd is not None and self.price_usd < 0:
            raise DomainValidationError("Product price_usd must be non-negative")
        if self.price_eur is not None and self.price_eur < 0:
            raise DomainValidationError("Product price_eur must be non-negative")
        if self.price_cny is not None and self.price_cny < 0:
            raise DomainValidationError("Product price_cny must be non-negative")
        if self.is_hidden not in (0, 1, 2):
            raise DomainValidationError("Product is_hidden must be 0, 1, or 2")
        self.effective_hidden = max(
            self.is_hidden, self.brand_products_hidden_override or 0
        )

    @property
    def is_available(self) -> bool:
        return (
            self.is_published and self.deleted_at is None and self.effective_hidden != 2
        )

    def resolve_price(self, variant: "ProductVariantDomain") -> Decimal:
        return variant.resolve_price(self.base_price)


@dataclass(slots=True, kw_only=True)
class ProductVariantDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    product_id: UUID
    sku: str
    size: str | None = field(default=None)
    color_name: str | None = field(default=None)
    color: str | None = field(default=None)
    created_by: UUID

    color_hex: str | None = field(default=None)
    price_override: Decimal | None = field(default=None)
    stock_quantity: int = field(default=0)
    orders_count: int = field(default=0)

    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)

    def __post_init__(self) -> None:
        if self.color_name is None and self.color is not None:
            self.color_name = self.color
        elif self.color is None and self.color_name is not None:
            self.color = self.color_name

        if self.stock_quantity < 0:
            raise DomainValidationError("Variant stock_quantity must be non-negative")
        if self.price_override is not None and self.price_override < 0:
            raise DomainValidationError("Variant price_override must be non-negative")

    def resolve_price(self, base_price: Decimal) -> Decimal:
        return self.price_override if self.price_override is not None else base_price


@dataclass(slots=True, kw_only=True)
class ProductImageDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    product_id: UUID
    url: str
    created_by: UUID

    variant_id: UUID | None = field(default=None)
    color: str | None = field(default=None)
    alt_text: str | None = field(default=None)
    sort_order: int = field(default=0)
    is_main: bool = field(default=False)

    created_at: datetime = field(default_factory=factory_now)
