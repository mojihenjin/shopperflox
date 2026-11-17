from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import get_admin_service, require_permission
from src.api.v1.schemas import (
    AdminBanUserRequest,
    AdminBrandResponse,
    AdminCategoryCreateRequest,
    AdminCategoryUpdateRequest,
    AdminHideProductsResponse,
    AdminReviewResponse,
    AdminUserBanResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
    BrandMemberResponse,
    BrandResponse,
    CategoryResponse,
    ProductResponse,
)
from src.application.services import AdminService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import ModerationStatus, UserDomain

router = APIRouter(prefix="/admin", tags=["Admin"])


# =====================================================================
# Users
# =====================================================================


@router.get(
    "/users",
    response_model=BaseResponse[list[AdminUserResponse]],
)
async def list_users(
    search: str | None = None,
    user_status: Literal["all", "active", "banned", "unbanned", "deleted"] = Query(
        default="all", alias="status"
    ),
    verified_profile: bool | None = None,
    sort_by: Literal["created_at", "login"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    users_with_bans, total = await admin_service.list_users(
        actor=admin,
        search=search,
        status=user_status,
        verified_profile=verified_profile,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )

    data = [
        AdminUserResponse(
            id=u.id,
            login=u.login,
            email=u.email,
            verified_profile=u.verified_profile,
            verified_email=u.verified_email,
            global_permissions=u.global_permissions,
            is_deleted=u.is_deleted,
            deleted_at=u.deleted_at,
            active_ban=AdminUserBanResponse.model_validate(ban) if ban else None,
            created_at=u.created_at,
        )
        for u, ban in users_with_bans
    ]

    return ResponseGenerator.answer(
        body=data,
        metadata={"total": total, "limit": limit, "offset": offset},
    )


@router.patch(
    "/users/{user_id}",
    response_model=BaseResponse[AdminUserResponse],
)
async def update_user(
    user_id: UUID,
    req: AdminUserUpdateRequest,
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    user, ban = await admin_service.update_user(
        actor=admin,
        target_user_id=user_id,
        login=req.login,
        global_permissions=req.global_permissions,
        verified_profile=req.verified_profile,
    )
    return ResponseGenerator.answer(
        body=AdminUserResponse(
            id=user.id,
            login=user.login,
            email=user.email,
            verified_profile=user.verified_profile,
            verified_email=user.verified_email,
            global_permissions=user.global_permissions,
            is_deleted=user.is_deleted,
            deleted_at=user.deleted_at,
            active_ban=AdminUserBanResponse.model_validate(ban) if ban else None,
            created_at=user.created_at,
        )
    )


@router.post(
    "/users/{user_id}/ban",
    response_model=BaseResponse[AdminUserBanResponse],
)
async def ban_user(
    user_id: UUID,
    req: AdminBanUserRequest,
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    ban = await admin_service.ban_user(
        actor=admin,
        target_user_id=user_id,
        reason=req.reason,
        ended_at=req.ended_at,
    )
    return ResponseGenerator.answer(body=AdminUserBanResponse.model_validate(ban))


@router.post(
    "/users/{user_id}/unban",
    response_model=BaseResponse[AdminUserBanResponse],
)
async def unban_user(
    user_id: UUID,
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    ban = await admin_service.unban_user(
        actor=admin,
        target_user_id=user_id,
    )
    return ResponseGenerator.answer(body=AdminUserBanResponse.model_validate(ban))


@router.delete(
    "/users/{user_id}",
    response_model=BaseResponse[dict[str, bool]],
)
async def delete_user(
    user_id: UUID,
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    await admin_service.delete_user(
        actor=admin,
        target_user_id=user_id,
    )
    return ResponseGenerator.answer(body={"success": True})


@router.post(
    "/users/{user_id}/reset-password",
    response_model=BaseResponse[dict[str, bool]],
)
async def reset_password(
    user_id: UUID,
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    await admin_service.reset_password(
        actor=admin,
        target_user_id=user_id,
    )
    return ResponseGenerator.answer(body={"success": True})


# =====================================================================
# Brands
# =====================================================================


@router.get(
    "/brands",
    response_model=BaseResponse[list[AdminBrandResponse]],
)
async def list_brands(
    search: str | None = None,
    moderation_status: ModerationStatus | None = None,
    is_verified: bool | None = None,
    include_deleted: bool = True,
    sort_by: Literal["created_at", "name", "views_count", "orders_count"] = (
        "created_at"
    ),
    sort_order: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    brands_with_members, total = await admin_service.list_brands(
        actor=admin,
        search=search,
        moderation_status=moderation_status.value if moderation_status else None,
        is_verified=is_verified,
        include_deleted=include_deleted,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )

    data = [
        AdminBrandResponse(
            id=b.id,
            name=b.name,
            slug=b.slug,
            description=getattr(b, "description", None),
            logo_url=b.logo_url,
            his_url=b.his_url,
            moderation_status=b.moderation_status,
            rejection_reason=b.rejection_reason,
            is_verified=b.is_verified,
            views_count=b.views_count,
            orders_count=b.orders_count,
            is_deleted=b.is_deleted,
            created_at=b.created_at,
            members=[BrandMemberResponse.model_validate(m) for m in members],
        )
        for b, members in brands_with_members
    ]

    return ResponseGenerator.answer(
        body=data,
        metadata={"total": total, "limit": limit, "offset": offset},
    )


@router.post(
    "/brands/{brand_id}/remoderate",
    response_model=BaseResponse[BrandResponse],
)
async def remoderate_brand(
    brand_id: UUID,
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    brand = await admin_service.remoderate_brand(
        actor=admin,
        brand_id=brand_id,
    )
    return ResponseGenerator.answer(body=BrandResponse.model_validate(brand))


@router.post(
    "/brands/{brand_id}/hide-all-products",
    response_model=BaseResponse[AdminHideProductsResponse],
)
async def hide_all_brand_products(
    brand_id: UUID,
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    count = await admin_service.hide_all_brand_products(
        actor=admin,
        brand_id=brand_id,
    )
    return ResponseGenerator.answer(body=AdminHideProductsResponse(updated_count=count))


# =====================================================================
# Categories
# =====================================================================


@router.get(
    "/categories",
    response_model=BaseResponse[list[CategoryResponse]],
)
async def list_categories(
    search: str | None = None,
    sort_by: Literal["sort_order", "created_at", "name"] = "sort_order",
    sort_order: Literal["asc", "desc"] = "asc",
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    categories = await admin_service.list_categories(
        actor=admin,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ResponseGenerator.answer(
        body=[CategoryResponse.model_validate(c) for c in categories]
    )


@router.post(
    "/categories",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[CategoryResponse],
)
async def create_category(
    req: AdminCategoryCreateRequest,
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    category = await admin_service.create_category(
        actor=admin,
        name=req.name,
        slug=req.slug,
        parent_id=req.parent_id,
        sort_order=req.sort_order,
    )
    return ResponseGenerator.answer(
        body=CategoryResponse.model_validate(category),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/categories/{category_id}",
    response_model=BaseResponse[CategoryResponse],
)
async def update_category(
    category_id: UUID,
    req: AdminCategoryUpdateRequest,
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    category = await admin_service.update_category(
        actor=admin,
        category_id=category_id,
        name=req.name,
        slug=req.slug,
        parent_id=req.parent_id,
        sort_order=req.sort_order,
    )
    return ResponseGenerator.answer(body=CategoryResponse.model_validate(category))


@router.delete(
    "/categories/{category_id}",
    response_model=BaseResponse[dict[str, bool]],
)
async def delete_category(
    category_id: UUID,
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    await admin_service.delete_category(
        actor=admin,
        category_id=category_id,
    )
    return ResponseGenerator.answer(body={"success": True})


# =====================================================================
# Products
# =====================================================================


@router.get(
    "/products",
    response_model=BaseResponse[list[ProductResponse]],
)
async def list_products(
    search: str | None = None,
    moderation_status: ModerationStatus | None = None,
    is_hidden: int | None = None,
    is_limited: bool | None = None,
    sort_by: Literal[
        "created_at", "base_price", "views_count", "orders_count", "title"
    ] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    products, total = await admin_service.list_products(
        actor=admin,
        search=search,
        moderation_status=moderation_status.value if moderation_status else None,
        is_hidden=is_hidden,
        is_limited=is_limited,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    return ResponseGenerator.answer(
        body=[ProductResponse.model_validate(p) for p in products],
        metadata={"total": total, "limit": limit, "offset": offset},
    )


@router.post(
    "/products/{product_id}/remoderate",
    response_model=BaseResponse[ProductResponse],
)
async def remoderate_product(
    product_id: UUID,
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    product = await admin_service.remoderate_product(
        actor=admin,
        product_id=product_id,
    )
    return ResponseGenerator.answer(body=ProductResponse.model_validate(product))


# =====================================================================
# Reviews
# =====================================================================


@router.get(
    "/reviews",
    response_model=BaseResponse[list[AdminReviewResponse]],
)
async def list_reviews(
    search: str | None = None,
    rating: int | None = Query(default=None, ge=1, le=5),
    sort_by: Literal["created_at", "rating"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    reviews_with_meta, total = await admin_service.list_reviews(
        actor=admin,
        search=search,
        rating=rating,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )

    data = [
        AdminReviewResponse(
            id=item.review.id,
            user_id=item.review.user_id,
            product_id=item.review.product_id,
            rating=item.review.rating,
            comment=item.review.comment,
            fit_feedback=item.review.fit_feedback,
            is_published=item.review.is_published,
            user_login=item.user_login,
            product_title=item.product_title,
            product_slug=item.product_slug,
            created_at=item.review.created_at,
        )
        for item in reviews_with_meta
    ]

    return ResponseGenerator.answer(
        body=data,
        metadata={"total": total, "limit": limit, "offset": offset},
    )


@router.delete(
    "/reviews/{review_id}",
    response_model=BaseResponse[dict[str, bool]],
)
async def delete_review(
    review_id: UUID,
    admin: UserDomain = Depends(require_permission("admin:access")),
    admin_service: AdminService = Depends(get_admin_service),
):
    await admin_service.delete_review(
        actor=admin,
        review_id=review_id,
    )
    return ResponseGenerator.answer(body={"success": True})
