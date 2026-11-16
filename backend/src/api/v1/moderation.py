from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import (
    get_catalog_service,
    get_moderation_service,
    require_permission,
)
from src.api.v1.schemas import (
    BanUserRequest,
    PendingCountResponse,
    ProductResponse,
    RejectProductRequest,
    SetPermissionsRequest,
    UserBanResponse,
    UserResponse,
)
from src.application.services import CatalogService, UserModerationService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import UserDomain

router = APIRouter(prefix="/moderation", tags=["Moderation"])


@router.post(
    "/users/{user_id}/ban",
    response_model=BaseResponse[UserBanResponse],
)
async def ban_user(
    user_id: UUID,
    req: BanUserRequest,
    moderator: UserDomain = Depends(require_permission("users:ban")),
    moderation_service: UserModerationService = Depends(get_moderation_service),
):
    ban = await moderation_service.ban_user(
        moderator_id=moderator.id,
        target_user_id=user_id,
        reason=req.reason,
        ended_at=req.ended_at,
    )
    return ResponseGenerator.answer(body=UserBanResponse.model_validate(ban))


@router.post(
    "/users/{user_id}/unban",
    response_model=BaseResponse[UserBanResponse],
)
async def unban_user(
    user_id: UUID,
    moderator: UserDomain = Depends(require_permission("users:ban")),
    moderation_service: UserModerationService = Depends(get_moderation_service),
):
    ban = await moderation_service.unban_user(
        moderator_id=moderator.id,
        target_user_id=user_id,
    )
    return ResponseGenerator.answer(body=UserBanResponse.model_validate(ban))


@router.put(
    "/users/{user_id}/permissions",
    response_model=BaseResponse[UserResponse],
)
async def set_user_permissions(
    user_id: UUID,
    req: SetPermissionsRequest,
    admin: UserDomain = Depends(require_permission("users:permissions")),
    moderation_service: UserModerationService = Depends(get_moderation_service),
):
    user = await moderation_service.set_permissions(
        admin_id=admin.id,
        target_user_id=user_id,
        permissions=req.permissions,
    )
    return ResponseGenerator.answer(body=UserResponse.model_validate(user))


@router.get(
    "/products",
    response_model=BaseResponse[list[ProductResponse]],
)
async def list_pending_products(
    request_type: Literal["CREATE", "EDIT"] | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    moderator: UserDomain = Depends(require_permission("mod:approve_manager")),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    products, total = await catalog_service.list_pending_products(
        actor=moderator,
        request_type=request_type,
        limit=limit,
        offset=offset,
    )
    return ResponseGenerator.answer(
        body=[ProductResponse.model_validate(p) for p in products],
        metadata={"total": total, "limit": limit, "offset": offset},
    )


@router.get(
    "/products/pending-count",
    response_model=BaseResponse[PendingCountResponse],
)
async def count_pending_products(
    moderator: UserDomain = Depends(require_permission("mod:approve_manager")),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    count = await catalog_service.count_pending_products(actor=moderator)
    return ResponseGenerator.answer(body=PendingCountResponse(pending_count=count))


@router.post(
    "/products/{product_id}/approve",
    response_model=BaseResponse[ProductResponse],
)
async def approve_product(
    product_id: UUID,
    moderator: UserDomain = Depends(require_permission("mod:approve_manager")),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    product = await catalog_service.approve_product(
        actor=moderator,
        product_id=product_id,
    )
    return ResponseGenerator.answer(body=ProductResponse.model_validate(product))


@router.post(
    "/products/{product_id}/reject",
    response_model=BaseResponse[ProductResponse],
)
async def reject_product(
    product_id: UUID,
    req: RejectProductRequest,
    moderator: UserDomain = Depends(require_permission("mod:approve_manager")),
    catalog_service: CatalogService = Depends(get_catalog_service),
):
    product = await catalog_service.reject_product(
        actor=moderator,
        product_id=product_id,
        reason=req.reason,
    )
    return ResponseGenerator.answer(body=ProductResponse.model_validate(product))
