from decimal import Decimal
from uuid import UUID

from uuid6 import uuid7

from src.domain.models import (
    FitFeedback,
    OrderDomain,
    OrderItemDomain,
    OrderStatus,
    PaymentDomain,
    PaymentStatus,
    ReviewDomain,
)


def test_order_domain():
    user_id = uuid7()
    order = OrderDomain(
        user_id=user_id,
        total_amount=Decimal("199.90"),
        shipping_address={"city": "Berlin", "street": "Alexanderplatz 1"},
        created_by=user_id,
    )

    assert isinstance(order.id, UUID)
    assert order.status == OrderStatus.PENDING_PAYMENT
    assert order.total_amount == Decimal("199.90")
    assert order.tracking_number is None


def test_order_item_domain():
    order_id = uuid7()
    author_id = uuid7()
    item = OrderItemDomain(
        order_id=order_id,
        title_snapshot="Sneakers",
        sku_snapshot="SNK-01",
        size_snapshot="43",
        color_snapshot="White",
        unit_price=Decimal("99.95"),
        quantity=2,
        created_by=author_id,
    )

    assert isinstance(item.id, UUID)
    assert item.order_id == order_id
    assert item.unit_price == Decimal("99.95")
    assert item.quantity == 2


def test_payment_domain():
    order_id = uuid7()
    payment = PaymentDomain(
        order_id=order_id,
        provider="stripe",
        amount=Decimal("199.90"),
        external_id="ch_123456",
    )

    assert isinstance(payment.id, UUID)
    assert payment.status == PaymentStatus.PENDING
    assert payment.provider == "stripe"
    assert payment.amount == Decimal("199.90")
    assert payment.external_id == "ch_123456"
    assert payment.paid_at is None


def test_review_domain():
    user_id = uuid7()
    product_id = uuid7()
    order_item_id = uuid7()

    review = ReviewDomain(
        user_id=user_id,
        product_id=product_id,
        order_item_id=order_item_id,
        rating=5,
        fit_feedback=FitFeedback.TRUE_TO_SIZE,
        comment="Great quality!",
        created_by=user_id,
    )

    assert isinstance(review.id, UUID)
    assert review.rating == 5
    assert review.is_published is True
    assert review.comment == "Great quality!"
