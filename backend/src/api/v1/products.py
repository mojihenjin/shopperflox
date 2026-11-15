from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_catalog_service, require_permission
from src.api.v1.schemas import (
    ProductCreateRequest,
    ProductDetailResponse,
    ProductImageCreateRequest,
    ProductImageResponse,
    ProductResponse,
    ProductUpdateRequest,
    ProductVariantCreateRequest,
    ProductVariantResponse,
    ProductVariantUpdateRequest,
)
from src.application.services import CatalogService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import UserDomain

router = APIRouter(tags=["Products"])


@router.get("/products", response_model=BaseResponse[list[ProductResponse]])
async def list_products(
    category_id: UUID | None = Query(default=None),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    products, total = await catalog_service.list_products(
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        search=search,
        limit=limit,
        offset=offset,
    )
    items = [ProductResponse.model_validate(p) for p in products]
    return ResponseGenerator.answer(
        body=items,
        metadata={"total": total, "limit": limit, "offset": offset},
    )


@router.get("/products/{slug}", response_model=BaseResponse[ProductDetailResponse])
async def get_product_detail(
    slug: str,
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    product, variants, images = await catalog_service.get_product_detail(slug)
    detail = ProductDetailResponse(
        product=ProductResponse.model_validate(product),
        variants=[ProductVariantResponse.model_validate(v) for v in variants],
        images=[ProductImageResponse.model_validate(img) for img in images],
    )
    return ResponseGenerator.answer(body=detail)


@router.post(
    "/products",
    response_model=BaseResponse[ProductResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    req: ProductCreateRequest,
    current_user: UserDomain = Depends(require_permission("catalog:manage")),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    product = await catalog_service.create_product(
        actor=current_user,
        category_id=req.category_id,
        title=req.title,
        slug=req.slug,
        base_price=req.base_price,
        description=req.description,
        attributes=req.attributes,
        is_published=req.is_published,
    )
    return ResponseGenerator.answer(
        body=ProductResponse.model_validate(product),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch("/products/{product_id}", response_model=BaseResponse[ProductResponse])
async def update_product(
    product_id: UUID,
    req: ProductUpdateRequest,
    current_user: UserDomain = Depends(require_permission("catalog:manage")),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    product = await catalog_service.update_product(
        actor=current_user,
        product_id=product_id,
        category_id=req.category_id,
        title=req.title,
        slug=req.slug,
        base_price=req.base_price,
        description=req.description,
        attributes=req.attributes,
        is_published=req.is_published,
    )
    return ResponseGenerator.answer(body=ProductResponse.model_validate(product))


@router.delete("/products/{product_id}", response_model=BaseResponse[None])
async def delete_product(
    product_id: UUID,
    current_user: UserDomain = Depends(require_permission("catalog:manage")),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    await catalog_service.delete_product(actor=current_user, product_id=product_id)
    return ResponseGenerator.answer(body=None)


@router.post(
    "/products/{product_id}/variants",
    response_model=BaseResponse[ProductVariantResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_product_variant(
    product_id: UUID,
    req: ProductVariantCreateRequest,
    current_user: UserDomain = Depends(require_permission("catalog:manage")),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    variant = await catalog_service.create_variant(
        actor=current_user,
        product_id=product_id,
        sku=req.sku,
        size=req.size,
        color_name=req.color_name,
        color_hex=req.color_hex,
        price_override=req.price_override,
        stock_quantity=req.stock_quantity,
    )
    return ResponseGenerator.answer(
        body=ProductVariantResponse.model_validate(variant),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/variants/{variant_id}",
    response_model=BaseResponse[ProductVariantResponse],
)
async def update_product_variant(
    variant_id: UUID,
    req: ProductVariantUpdateRequest,
    current_user: UserDomain = Depends(require_permission("catalog:manage")),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    variant = await catalog_service.update_variant(
        actor=current_user,
        variant_id=variant_id,
        sku=req.sku,
        size=req.size,
        color_name=req.color_name,
        color_hex=req.color_hex,
        price_override=req.price_override,
        stock_quantity=req.stock_quantity,
    )
    return ResponseGenerator.answer(body=ProductVariantResponse.model_validate(variant))


@router.post(
    "/products/{product_id}/images",
    response_model=BaseResponse[ProductImageResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_product_image(
    product_id: UUID,
    req: ProductImageCreateRequest,
    current_user: UserDomain = Depends(require_permission("catalog:manage")),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    image = await catalog_service.add_image(
        actor=current_user,
        product_id=product_id,
        url=req.url,
        variant_id=req.variant_id,
        alt_text=req.alt_text,
        sort_order=req.sort_order,
        is_main=req.is_main,
    )
    return ResponseGenerator.answer(
        body=ProductImageResponse.model_validate(image),
        status_code=status.HTTP_201_CREATED,
    )
