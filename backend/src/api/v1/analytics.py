from uuid import UUID

from fastapi import APIRouter, Depends

from src.api.dependencies import get_analytics_service, get_current_user
from src.api.v1.schemas.analytics import SalesAnalyticsResponse
from src.application.services import AnalyticsService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import UserDomain

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/my", response_model=BaseResponse[SalesAnalyticsResponse])
async def get_my_analytics(
    current_user: UserDomain = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    analytics = await analytics_service.get_my_analytics(actor=current_user)
    resp = SalesAnalyticsResponse.model_validate(analytics)
    return ResponseGenerator.answer(body=resp, status_code=200)


@router.get("/brands/{brand_id}", response_model=BaseResponse[SalesAnalyticsResponse])
async def get_brand_analytics(
    brand_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    analytics = await analytics_service.get_brand_analytics(
        actor=current_user, brand_id=brand_id
    )
    resp = SalesAnalyticsResponse.model_validate(analytics)
    return ResponseGenerator.answer(body=resp, status_code=200)
