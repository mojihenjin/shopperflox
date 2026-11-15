from pydantic import BaseModel, ConfigDict

from src.api.v1.schemas.catalog import ProductResponse, ProductVariantResponse


class BrandSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    products_count: int


class SearchResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    products: list[ProductResponse]
    brands: list[BrandSearchResponse]
    variants: list[ProductVariantResponse]
