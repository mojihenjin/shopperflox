from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_current_user, get_notification_service
from src.api.v1.schemas import (
    NotificationResponse,
    ReadAllNotificationsResponse,
    UnreadCountResponse,
)
from src.application.services import NotificationService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import UserDomain

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=BaseResponse[list[NotificationResponse]])
async def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserDomain = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    items, total = await notification_service.list_notifications(
        user_id=current_user.id, limit=limit, offset=offset
    )
    res = [NotificationResponse.model_validate(n) for n in items]
    return ResponseGenerator.answer(
        body=res,
        metadata={"total": total, "limit": limit, "offset": offset},
    )


@router.get("/unread-count", response_model=BaseResponse[UnreadCountResponse])
async def get_unread_count(
    current_user: UserDomain = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    count = await notification_service.get_unread_count(user_id=current_user.id)
    return ResponseGenerator.answer(body=UnreadCountResponse(count=count))


@router.patch(
    "/{notification_id}/read", response_model=BaseResponse[NotificationResponse]
)
async def mark_as_read(
    notification_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    notification = await notification_service.mark_read(
        notification_id=notification_id, user_id=current_user.id
    )
    return ResponseGenerator.answer(
        body=NotificationResponse.model_validate(notification)
    )


@router.post("/read-all", response_model=BaseResponse[ReadAllNotificationsResponse])
async def mark_all_as_read(
    current_user: UserDomain = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    marked_count = await notification_service.mark_all_read(user_id=current_user.id)
    return ResponseGenerator.answer(
        body=ReadAllNotificationsResponse(marked_count=marked_count)
    )
