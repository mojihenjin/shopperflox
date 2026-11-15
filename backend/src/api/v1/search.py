from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_catalog_service
from src.api.v1.schemas.catalog import ProductResponse, ProductVariantResponse
from src.api.v1.schemas.search import BrandSearchResponse, SearchResultResponse
from src.application.services import CatalogService
from src.core import BaseResponse, ResponseGenerator

router = APIRouter(tags=["Search"])


@router.get("/search", response_model=BaseResponse[SearchResultResponse])
async def search_catalog(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=10, ge=1, le=50),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    result = await catalog_service.search(query=q, limit=limit)
    response_data = SearchResultResponse(
        products=[ProductResponse.model_validate(p) for p in result.products],
        brands=[BrandSearchResponse.model_validate(b) for b in result.brands],
        variants=[ProductVariantResponse.model_validate(v) for v in result.variants],
    )
    return ResponseGenerator.answer(body=response_data)
