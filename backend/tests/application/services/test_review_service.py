from decimal import Decimal

import pytest
from uuid6 import uuid7

from src.application.services import ReviewService
from src.domain.exceptions import (
    EntityAlreadyExistsError,
    PermissionDeniedError,
)
from src.domain.models import FitFeedback, ProductDomain, UserDomain

pytestmark = pytest.mark.anyio


async def test_review_service_flow(review_uow):
    service = ReviewService(uow=review_uow)
    user_id = uuid7()
    user = UserDomain(id=user_id, login="reviewer")
    product_id = uuid7()

    product = ProductDomain(
        id=product_id,
        category_id=uuid7(),
        title="Boots",
        slug="boots",
        base_price=Decimal("120.00"),
        is_published=True,
        created_by=user_id,
    )
    await review_uow.products.add(product)

    # 1. Unverified buyer cannot review
    with pytest.raises(PermissionDeniedError, match="Only verified buyers"):
        await service.create_review(
            user_id=user_id,
            product_id=product_id,
            rating=5,
            comment="Awesome!",
        )

    # Mock user has purchased product
    async def mock_has_purchased(uid, pid):
        return uid == user_id and pid == product_id

    review_uow.orders.has_user_purchased_product = mock_has_purchased

    # 2. Verified buyer successfully creates review
    review = await service.create_review(
        user_id=user_id,
        product_id=product_id,
        rating=5,
        fit_feedback=FitFeedback.TRUE_TO_SIZE,
        comment="Awesome!",
    )
    assert review.rating == 5
    assert review.fit_feedback == FitFeedback.TRUE_TO_SIZE

    # 3. Duplicate review fails
    with pytest.raises(EntityAlreadyExistsError, match="already reviewed"):
        await service.create_review(
            user_id=user_id,
            product_id=product_id,
            rating=4,
        )

    # 4. List reviews
    reviews, total = await service.list_product_reviews(product_id)
    assert total == 1
    assert len(reviews) == 1

    # 5. Author can delete review
    await service.delete_review(actor=user, review_id=review.id)
    reviews_after, total_after = await service.list_product_reviews(product_id)
    assert total_after == 0
