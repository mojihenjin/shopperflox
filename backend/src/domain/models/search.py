from dataclasses import dataclass

from .product import ProductDomain, ProductVariantDomain


@dataclass(slots=True, frozen=True)
class BrandSearchResult:
    name: str
    products_count: int


@dataclass(slots=True, frozen=True)
class SearchResultDomain:
    products: list[ProductDomain]
    brands: list[BrandSearchResult]
    variants: list[ProductVariantDomain]
