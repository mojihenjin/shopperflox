from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    parent_id: UUID | None = None
    sort_order: int = 0


class CategoryUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: UUID | None = None
    sort_order: int | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    parent_id: UUID | None = None
    sort_order: int = 0
    created_at: datetime


class VariantCreateItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    color: str | None = Field(default=None, max_length=64)
    color_name: str | None = Field(default=None, max_length=64)
    size: str | None = Field(default=None, max_length=64)
    stock_quantity: int = Field(default=0, ge=0)
    sku: str | None = Field(default=None, max_length=64)
    price_override: Decimal | None = Field(default=None, ge=0)
    color_hex: str | None = Field(default=None, max_length=32)


class ProductCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category_id: UUID
    brand_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255)
    brand: str | None = Field(default=None, max_length=128)
    is_self_worked: bool = False
    base_price: Decimal = Field(ge=0)
    price_usd: Decimal | None = Field(default=None, ge=0)
    price_eur: Decimal | None = Field(default=None, ge=0)

    material: str | None = Field(default=None, max_length=255)
    density: str | None = Field(default=None, max_length=128)
    composition: str | None = Field(default=None, max_length=255)
    print_method: str | None = Field(default=None, max_length=255)
    note: str | None = None

    description: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    is_published: bool = False
    is_hidden: Literal[0, 1, 2] = 0
    is_limited: bool = False
    variants: list[VariantCreateItem] = Field(default_factory=list)


class ProductUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category_id: UUID | None = None
    brand_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    brand: str | None = Field(default=None, max_length=128)
    is_self_worked: bool | None = None
    base_price: Decimal | None = Field(default=None, ge=0)
    price_usd: Decimal | None = Field(default=None, ge=0)
    price_eur: Decimal | None = Field(default=None, ge=0)

    material: str | None = Field(default=None, max_length=255)
    density: str | None = Field(default=None, max_length=128)
    composition: str | None = Field(default=None, max_length=255)
    print_method: str | None = Field(default=None, max_length=255)
    note: str | None = None

    description: str | None = None
    attributes: dict[str, Any] | None = None
    is_published: bool | None = None
    is_hidden: Literal[0, 1, 2] | None = None
    is_limited: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    creator_id: UUID | None = None
    brand_id: UUID | None = None
    title: str
    slug: str
    brand: str | None = None
    brand_slug: str | None = None
    brand_is_deleted: bool = False
    is_self_worked: bool = False
    base_price: Decimal
    price_usd: Decimal | None = None
    price_eur: Decimal | None = None

    material: str | None = None
    density: str | None = None
    composition: str | None = None
    print_method: str | None = None
    note: str | None = None

    description: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    is_published: bool = False
    is_hidden: int = 0
    is_limited: bool = False
    moderation_status: str = "pending"
    request_type: str = "CREATE"
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ProductVariantCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sku: str = Field(min_length=1, max_length=64)
    size: str | None = Field(default=None, max_length=64)
    color_name: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=64)
    color_hex: str | None = Field(default=None, max_length=32)
    price_override: Decimal | None = Field(default=None, ge=0)
    stock_quantity: int = Field(default=0, ge=0)


class ProductVariantUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sku: str | None = Field(default=None, min_length=1, max_length=64)
    size: str | None = Field(default=None, max_length=64)
    color_name: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=64)
    color_hex: str | None = Field(default=None, max_length=32)
    price_override: Decimal | None = Field(default=None, ge=0)
    stock_quantity: int | None = Field(default=None, ge=0)


class ProductVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    sku: str
    size: str | None = None
    color_name: str | None = None
    color: str | None = None
    color_hex: str | None = None
    price_override: Decimal | None = None
    stock_quantity: int = 0
    created_at: datetime
    updated_at: datetime


class ProductImageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: str = Field(min_length=1, max_length=512)
    variant_id: UUID | None = None
    color: str | None = Field(default=None, max_length=100)
    alt_text: str | None = Field(default=None, max_length=255)
    sort_order: int = 0
    is_main: bool = False


class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    variant_id: UUID | None = None
    color: str | None = None
    url: str
    alt_text: str | None = None
    sort_order: int = 0
    is_main: bool = False
    created_at: datetime


class ProductDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product: ProductResponse
    variants: list[ProductVariantResponse] = Field(default_factory=list)
    images: list[ProductImageResponse] = Field(default_factory=list)
