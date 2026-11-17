from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID


@dataclass(slots=True, kw_only=True)
class VariantSalesStats:
    variant_id: UUID
    sku: str
    color: str | None = None
    size: str | None = None
    stock_quantity: int = 0
    units_sold: int = 0
    revenue: dict[str, Decimal] = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class ProductSalesStats:
    product_id: UUID
    title: str
    slug: str
    views_count: int = 0
    units_sold: int = 0
    revenue: dict[str, Decimal] = field(default_factory=dict)
    variants: list[VariantSalesStats] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class SalesAnalyticsDomain:
    total_views: int = 0
    total_units_sold: int = 0
    total_revenue: dict[str, Decimal] = field(default_factory=dict)
    products: list[ProductSalesStats] = field(default_factory=list)
