from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.domain.exceptions import DomainValidationError
from src.utils import factory_now
from uuid6 import uuid7

from .base import BaseDomain


@dataclass(slots=True, kw_only=True)
class ProductDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    category_id: UUID
    title: str
    slug: str
    base_price: Decimal
    created_by: UUID

    description: str | None = field(default=None)
    attributes: dict[str, Any] = field(default_factory=dict)
    is_published: bool = field(default=False)

    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)
    deleted_at: datetime | None = field(default=None)

    def __post_init__(self) -> None:
        if self.base_price < 0:
            raise DomainValidationError("Product base_price must be non-negative")

    @property
    def is_available(self) -> bool:
        return self.is_published and self.deleted_at is None


@dataclass(slots=True, kw_only=True)
class ProductVariantDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    product_id: UUID
    sku: str
    size: str
    color_name: str
    created_by: UUID

    color_hex: str | None = field(default=None)
    price_override: Decimal | None = field(default=None)
    stock_quantity: int = field(default=0)

    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)

    def __post_init__(self) -> None:
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
    alt_text: str | None = field(default=None)
    sort_order: int = field(default=0)
    is_main: bool = field(default=False)

    created_at: datetime = field(default_factory=factory_now)
