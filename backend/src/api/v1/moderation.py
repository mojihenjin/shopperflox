from uuid import UUID

from fastapi import APIRouter, Depends

from src.api.dependencies import get_moderation_service, require_permission
from src.api.v1.schemas import (
    BanUserRequest,
    SetPermissionsRequest,
    UserBanResponse,
    UserResponse,
)
from src.application.services import UserModerationService
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
