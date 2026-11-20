from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_current_user, get_queue_service
from src.api.v1.schemas.queue import QueueItemResponse, QueueItemUpdateRequest
from src.application.services import QueueService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import FulfillmentStatus, UserDomain

router = APIRouter(prefix="/queue", tags=["Fulfillment Queue"])


@router.get("/my", response_model=BaseResponse[list[QueueItemResponse]])
async def get_my_queue(
    status: FulfillmentStatus | None = Query(default=None),
    current_user: UserDomain = Depends(get_current_user),
    queue_service: QueueService = Depends(get_queue_service),
):
    items = await queue_service.list_my_queue(actor=current_user, status=status)
    resp = [QueueItemResponse.model_validate(item) for item in items]
    return ResponseGenerator.answer(body=resp, status_code=200)


@router.get("/brands/{brand_id}", response_model=BaseResponse[list[QueueItemResponse]])
async def get_brand_queue(
    brand_id: UUID,
    status: FulfillmentStatus | None = Query(default=None),
    current_user: UserDomain = Depends(get_current_user),
    queue_service: QueueService = Depends(get_queue_service),
):
    items = await queue_service.list_brand_queue(
        actor=current_user, brand_id=brand_id, status=status
    )
    resp = [QueueItemResponse.model_validate(item) for item in items]
    return ResponseGenerator.answer(body=resp, status_code=200)


@router.patch("/items/{item_id}", response_model=BaseResponse[QueueItemResponse])
async def update_queue_item(
    item_id: UUID,
    req: QueueItemUpdateRequest,
    current_user: UserDomain = Depends(get_current_user),
    queue_service: QueueService = Depends(get_queue_service),
):
    item = await queue_service.update_item(
        actor=current_user,
        item_id=item_id,
        fulfillment_status=req.fulfillment_status,
        post_code=req.post_code,
        tracking_url=req.tracking_url,
    )
    resp = QueueItemResponse.model_validate(item)
    return ResponseGenerator.answer(body=resp, status_code=200)
