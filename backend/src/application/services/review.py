from uuid import UUID

from src.domain.exceptions import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    PermissionDeniedError,
)
from src.domain.interfaces import ReviewUnitOfWorkProtocol
from src.domain.models import FitFeedback, ReviewDomain, UserDomain


class ReviewService:
    def __init__(self, uow: ReviewUnitOfWorkProtocol) -> None:
        self.uow = uow

    async def create_review(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
        rating: int,
        fit_feedback: FitFeedback | str | None = None,
        comment: str | None = None,
    ) -> ReviewDomain:
        async with self.uow:
            product = await self.uow.products.get_by_id(product_id)
            if product is None or product.deleted_at is not None:
                raise EntityNotFoundError("Product not found")

            has_purchased = await self.uow.orders.has_user_purchased_product(
                user_id, product_id
            )
            if not has_purchased:
                raise PermissionDeniedError(
                    "Only verified buyers can review this product"
                )

            existing = await self.uow.reviews.get_by_user_and_product(
                user_id, product_id
            )
            if existing is not None:
                raise EntityAlreadyExistsError("User has already reviewed this product")

            parsed_feedback = (
                FitFeedback(fit_feedback)
                if isinstance(fit_feedback, str)
                else fit_feedback
            )

            review = ReviewDomain(
                user_id=user_id,
                product_id=product_id,
                order_item_id=None,
                rating=rating,
                fit_feedback=parsed_feedback,
                comment=comment,
                created_by=user_id,
            )

            await self.uow.reviews.add(review)
            await self.uow.commit()
            return review

    async def list_product_reviews(
        self, product_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[ReviewDomain], int]:
        async with self.uow:
            return await self.uow.reviews.list_by_product_id(
                product_id, limit=limit, offset=offset
            )

    async def delete_review(self, actor: UserDomain, review_id: UUID) -> None:
        async with self.uow:
            review = await self.uow.reviews.get_by_id(review_id)
            if review is None:
                raise EntityNotFoundError("Review not found")

            is_author = review.user_id == actor.id
            is_moderator = (
                "reviews:moderate" in actor.global_permissions
                or "*" in actor.global_permissions
            )
            if not (is_author or is_moderator):
                raise PermissionDeniedError("Access denied to review resource")

            await self.uow.reviews.delete(review.id)
            await self.uow.commit()
