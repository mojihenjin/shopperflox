from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from src.api.dependencies import (
    get_catalog_service,
    get_optional_current_user,
    require_catalog_or_creator_permission,
)
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
    current_user: UserDomain | None = Depends(get_optional_current_user),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    product, variants, images = await catalog_service.get_product_detail(
        slug, actor=current_user
    )
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
    current_user: UserDomain = Depends(require_catalog_or_creator_permission()),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    product = await catalog_service.create_product(
        actor=current_user,
        category_id=req.category_id,
        brand_id=req.brand_id,
        title=req.title,
        slug=req.slug,
        brand=req.brand,
        is_self_worked=req.is_self_worked,
        base_price=req.base_price,
        price_usd=req.price_usd,
        price_eur=req.price_eur,
        material=req.material,
        density=req.density,
        composition=req.composition,
        print_method=req.print_method,
        note=req.note,
        description=req.description,
        attributes=req.attributes,
        is_published=req.is_published,
        is_hidden=req.is_hidden,
        is_limited=req.is_limited,
        variants=[v.model_dump() for v in req.variants] if req.variants else None,
    )
    return ResponseGenerator.answer(
        body=ProductResponse.model_validate(product),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch("/products/{product_id}", response_model=BaseResponse[ProductResponse])
async def update_product(
    product_id: UUID,
    req: ProductUpdateRequest,
    current_user: UserDomain = Depends(require_catalog_or_creator_permission()),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    product = await catalog_service.update_product(
        actor=current_user,
        product_id=product_id,
        category_id=req.category_id,
        brand_id=req.brand_id if "brand_id" in req.model_fields_set else ...,
        title=req.title,
        slug=req.slug,
        brand=req.brand if "brand" in req.model_fields_set else ...,
        is_self_worked=req.is_self_worked,
        base_price=req.base_price,
        price_usd=req.price_usd if "price_usd" in req.model_fields_set else ...,
        price_eur=req.price_eur if "price_eur" in req.model_fields_set else ...,
        material=req.material if "material" in req.model_fields_set else ...,
        density=req.density if "density" in req.model_fields_set else ...,
        composition=req.composition if "composition" in req.model_fields_set else ...,
        print_method=req.print_method
        if "print_method" in req.model_fields_set
        else ...,
        note=req.note if "note" in req.model_fields_set else ...,
        description=req.description,
        attributes=req.attributes,
        is_published=req.is_published,
        is_hidden=req.is_hidden if "is_hidden" in req.model_fields_set else None,
        is_limited=req.is_limited if "is_limited" in req.model_fields_set else None,
    )
    return ResponseGenerator.answer(body=ProductResponse.model_validate(product))


@router.delete("/products/{product_id}", response_model=BaseResponse[None])
async def delete_product(
    product_id: UUID,
    current_user: UserDomain = Depends(require_catalog_or_creator_permission()),
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
    current_user: UserDomain = Depends(require_catalog_or_creator_permission()),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    color = req.color or req.color_name
    variant = await catalog_service.create_variant(
        actor=current_user,
        product_id=product_id,
        sku=req.sku,
        size=req.size,
        color_name=color,
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
    current_user: UserDomain = Depends(require_catalog_or_creator_permission()),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    color = req.color or req.color_name
    variant = await catalog_service.update_variant(
        actor=current_user,
        variant_id=variant_id,
        sku=req.sku,
        size=req.size,
        color_name=color,
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
    current_user: UserDomain = Depends(require_catalog_or_creator_permission()),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    image = await catalog_service.add_image(
        actor=current_user,
        product_id=product_id,
        url=req.url,
        variant_id=req.variant_id,
        color=req.color,
        alt_text=req.alt_text,
        sort_order=req.sort_order,
        is_main=req.is_main,
    )
    return ResponseGenerator.answer(
        body=ProductImageResponse.model_validate(image),
        status_code=status.HTTP_201_CREATED,
    )


@router.post(
    "/products/{product_id}/images/upload",
    response_model=BaseResponse[ProductImageResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_product_image(
    product_id: UUID,
    file: UploadFile = File(...),
    color: str | None = Form(default=None),
    alt_text: str | None = Form(default=None),
    sort_order: int = Form(default=0),
    is_main: bool = Form(default=False),
    current_user: UserDomain = Depends(require_catalog_or_creator_permission()),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    data = await file.read()
    image = await catalog_service.upload_product_image(
        actor=current_user,
        product_id=product_id,
        file_data=data,
        color=color,
        alt_text=alt_text,
        sort_order=sort_order,
        is_main=is_main,
    )
    return ResponseGenerator.answer(
        body=ProductImageResponse.model_validate(image),
        status_code=status.HTTP_201_CREATED,
    )


@router.delete(
    "/products/{product_id}/images/{image_id}",
    response_model=BaseResponse[None],
    status_code=status.HTTP_200_OK,
)
async def delete_product_image(
    product_id: UUID,
    image_id: UUID,
    current_user: UserDomain = Depends(require_catalog_or_creator_permission()),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    await catalog_service.delete_image(
        actor=current_user,
        product_id=product_id,
        image_id=image_id,
    )
    return ResponseGenerator.answer(body=None, status_code=status.HTTP_200_OK)
