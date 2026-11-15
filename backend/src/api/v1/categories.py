from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_catalog_service, require_permission
from src.api.v1.schemas import (
    CategoryCreateRequest,
    CategoryResponse,
)
from src.application.services import CatalogService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import UserDomain

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=BaseResponse[list[CategoryResponse]])
async def list_categories(
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    categories = await catalog_service.get_categories()
    items = [CategoryResponse.model_validate(c) for c in categories]
    return ResponseGenerator.answer(body=items)


@router.post(
    "",
    response_model=BaseResponse[CategoryResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    req: CategoryCreateRequest,
    current_user: UserDomain = Depends(require_permission("catalog:manage")),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    category = await catalog_service.create_category(
        actor=current_user,
        name=req.name,
        slug=req.slug,
        parent_id=req.parent_id,
        sort_order=req.sort_order,
    )
    return ResponseGenerator.answer(
        body=CategoryResponse.model_validate(category),
        status_code=status.HTTP_201_CREATED,
    )
