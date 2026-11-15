from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_current_user, get_review_service
from src.api.v1.schemas.review import CreateReviewRequest, ReviewResponse
from src.application.services import ReviewService
from src.core import BaseResponse, ResponseGenerator
from src.domain.models import UserDomain

router = APIRouter(tags=["Reviews"])


@router.get(
    "/products/{product_id}/reviews",
    response_model=BaseResponse[list[ReviewResponse]],
)
async def list_product_reviews(
    product_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    review_service: ReviewService = Depends(get_review_service),
):
    reviews, total = await review_service.list_product_reviews(
        product_id=product_id, limit=limit, offset=offset
    )
    result = [
        ReviewResponse(
            id=r.id,
            user_id=r.user_id,
            product_id=r.product_id,
            rating=r.rating,
            fit_feedback=r.fit_feedback,
            comment=r.comment,
            created_at=r.created_at,
        )
        for r in reviews
    ]
    return ResponseGenerator.answer(
        body=result,
        metadata={"total": total, "limit": limit, "offset": offset},
    )


@router.post(
    "/products/{product_id}/reviews",
    response_model=BaseResponse[ReviewResponse],
    status_code=201,
)
async def create_product_review(
    product_id: UUID,
    req: CreateReviewRequest,
    current_user: UserDomain = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
):
    review = await review_service.create_review(
        user_id=current_user.id,
        product_id=product_id,
        rating=req.rating,
        fit_feedback=req.fit_feedback,
        comment=req.comment,
    )
    resp = ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        product_id=review.product_id,
        rating=review.rating,
        fit_feedback=review.fit_feedback,
        comment=review.comment,
        created_at=review.created_at,
    )
    return ResponseGenerator.answer(body=resp, status_code=201)


@router.delete("/reviews/{review_id}", response_model=BaseResponse[dict[str, bool]])
async def delete_review(
    review_id: UUID,
    current_user: UserDomain = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service),
):
    await review_service.delete_review(
        actor=current_user,
        review_id=review_id,
    )
    return ResponseGenerator.answer(body={"deleted": True})
