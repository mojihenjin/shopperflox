from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VariantSalesStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    variant_id: UUID
    sku: str
    color: str | None = None
    size: str | None = None
    stock_quantity: int = 0
    units_sold: int = 0
    revenue: dict[str, Decimal]


class ProductSalesStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    title: str
    slug: str
    views_count: int = 0
    units_sold: int = 0
    revenue: dict[str, Decimal]
    variants: list[VariantSalesStatsResponse]


class SalesAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_views: int = 0
    total_units_sold: int = 0
    total_revenue: dict[str, Decimal]
    products: list[ProductSalesStatsResponse]
