from datetime import UTC, datetime
from decimal import Decimal

import pytest
from uuid6 import uuid7

from src.domain.exceptions import DomainValidationError, InvalidStateTransitionError
from src.domain.models import (
    CartDomain,
    CartItemDomain,
    OrderDomain,
    OrderItemDomain,
    OrderStatus,
    PaymentDomain,
    PaymentStatus,
    ProductDomain,
    ProductVariantDomain,
    ReviewDomain,
)


def test_cart_owner_invariant():
    # Neither user_id nor session_token -> raises DomainValidationError
    with pytest.raises(DomainValidationError, match="Cart must have an owner"):
        CartDomain()

    with pytest.raises(DomainValidationError, match="Cart must have an owner"):
        CartDomain(user_id=None, session_token="")

    # Valid with user_id
    cart_user = CartDomain(user_id=uuid7())
    assert cart_user.user_id is not None

    # Valid with session_token
    cart_session = CartDomain(session_token="sess-token-123")
    assert cart_session.session_token == "sess-token-123"


def test_cart_item_quantity_invariant():
    cart_id = uuid7()
    variant_id = uuid7()

    with pytest.raises(DomainValidationError, match="quantity must be greater than zero"):
        CartItemDomain(cart_id=cart_id, variant_id=variant_id, quantity=0)

    with pytest.raises(DomainValidationError, match="quantity must be greater than zero"):
        CartItemDomain(cart_id=cart_id, variant_id=variant_id, quantity=-2)

    valid_item = CartItemDomain(cart_id=cart_id, variant_id=variant_id, quantity=1)
    assert valid_item.quantity == 1


def test_product_invariants_and_availability():
    author_id = uuid7()
    category_id = uuid7()

    # Negative price -> error
    with pytest.raises(DomainValidationError, match="base_price must be non-negative"):
        ProductDomain(
            category_id=category_id,
            title="Book",
            slug="book",
            base_price=Decimal("-1.00"),
            created_by=author_id,
        )

    # Valid product
    prod = ProductDomain(
        category_id=category_id,
        title="Book",
        slug="book",
        base_price=Decimal("15.00"),
        created_by=author_id,
        is_published=False,
    )
    assert prod.is_available is False

    prod.is_published = True
    assert prod.is_available is True

    prod.deleted_at = datetime.now(tz=UTC)
    assert prod.is_available is False


def test_product_variant_invariants_and_resolve_price():
    author_id = uuid7()
    prod_id = uuid7()

    with pytest.raises(DomainValidationError, match="stock_quantity must be non-negative"):
        ProductVariantDomain(
            product_id=prod_id,
            sku="SKU-1",
            size="M",
            color_name="Red",
            stock_quantity=-5,
            created_by=author_id,
        )

    with pytest.raises(DomainValidationError, match="price_override must be non-negative"):
        ProductVariantDomain(
            product_id=prod_id,
            sku="SKU-2",
            size="L",
            color_name="Blue",
            price_override=Decimal("-10.00"),
            created_by=author_id,
        )

    # resolve_price without override
    var_no_override = ProductVariantDomain(
        product_id=prod_id,
        sku="SKU-3",
        size="S",
        color_name="Green",
        created_by=author_id,
    )
    assert var_no_override.resolve_price(base_price=Decimal("50.00")) == Decimal("50.00")

    # resolve_price with override
    var_with_override = ProductVariantDomain(
        product_id=prod_id,
        sku="SKU-4",
        size="XL",
        color_name="Black",
        price_override=Decimal("45.00"),
        created_by=author_id,
    )
    assert var_with_override.resolve_price(base_price=Decimal("50.00")) == Decimal("45.00")


def test_order_invariants_and_transitions():
    user_id = uuid7()

    with pytest.raises(DomainValidationError, match="total_amount must be non-negative"):
        OrderDomain(
            user_id=user_id,
            total_amount=Decimal("-0.01"),
            shipping_address={"city": "Rome"},
            created_by=user_id,
        )

    order = OrderDomain(
        user_id=user_id,
        total_amount=Decimal("100.00"),
        shipping_address={"city": "Rome"},
        created_by=user_id,
    )
    assert order.status == OrderStatus.PENDING_PAYMENT

    # Valid transition PENDING_PAYMENT -> PAID
    old_updated_at = order.updated_at
    order.transition_to(OrderStatus.PAID)
    assert order.status == OrderStatus.PAID
    assert order.updated_at >= old_updated_at

    # Valid transition PAID -> PROCESSING -> SHIPPED -> DELIVERED -> REFUNDED
    order.transition_to(OrderStatus.PROCESSING)
    assert order.status == OrderStatus.PROCESSING

    order.transition_to(OrderStatus.SHIPPED)
    assert order.status == OrderStatus.SHIPPED

    order.transition_to(OrderStatus.DELIVERED)
    assert order.status == OrderStatus.DELIVERED

    order.transition_to(OrderStatus.REFUNDED)
    assert order.status == OrderStatus.REFUNDED

    # Terminal state: cannot transition from REFUNDED
    with pytest.raises(InvalidStateTransitionError, match="Cannot transition order"):
        order.transition_to(OrderStatus.PAID)


def test_order_forbidden_transition():
    user_id = uuid7()
    order = OrderDomain(
        user_id=user_id,
        total_amount=Decimal("50.00"),
        shipping_address={"city": "Paris"},
        created_by=user_id,
    )
    # Direct jump from PENDING_PAYMENT to DELIVERED is forbidden
    with pytest.raises(InvalidStateTransitionError):
        order.transition_to(OrderStatus.DELIVERED)


def test_order_item_invariants():
    order_id = uuid7()
    author_id = uuid7()

    with pytest.raises(DomainValidationError, match="unit_price must be non-negative"):
        OrderItemDomain(
            order_id=order_id,
            title_snapshot="Hat",
            sku_snapshot="HAT-1",
            size_snapshot="OneSize",
            color_snapshot="Brown",
            unit_price=Decimal("-5.00"),
            quantity=1,
            created_by=author_id,
        )

    with pytest.raises(DomainValidationError, match="quantity must be greater than zero"):
        OrderItemDomain(
            order_id=order_id,
            title_snapshot="Hat",
            sku_snapshot="HAT-1",
            size_snapshot="OneSize",
            color_snapshot="Brown",
            unit_price=Decimal("15.00"),
            quantity=0,
            created_by=author_id,
        )


def test_payment_invariants_and_transitions():
    order_id = uuid7()

    with pytest.raises(DomainValidationError, match="Payment amount must be non-negative"):
        PaymentDomain(
            order_id=order_id,
            provider="paypal",
            amount=Decimal("-10.00"),
        )

    payment = PaymentDomain(
        order_id=order_id,
        provider="stripe",
        amount=Decimal("100.00"),
    )
    assert payment.status == PaymentStatus.PENDING
    assert payment.paid_at is None

    # PENDING -> SUCCEEDED sets paid_at
    payment.transition_to(PaymentStatus.SUCCEEDED)
    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.paid_at is not None

    # SUCCEEDED -> REFUNDED
    payment.transition_to(PaymentStatus.REFUNDED)
    assert payment.status == PaymentStatus.REFUNDED

    # Terminal state: cannot transition from REFUNDED
    with pytest.raises(InvalidStateTransitionError, match="Cannot transition payment"):
        payment.transition_to(PaymentStatus.SUCCEEDED)


def test_payment_failed_terminal():
    order_id = uuid7()
    payment = PaymentDomain(
        order_id=order_id,
        provider="stripe",
        amount=Decimal("100.00"),
    )
    payment.transition_to(PaymentStatus.FAILED)
    assert payment.status == PaymentStatus.FAILED

    with pytest.raises(InvalidStateTransitionError):
        payment.transition_to(PaymentStatus.SUCCEEDED)


def test_review_rating_invariant():
    user_id = uuid7()
    prod_id = uuid7()
    item_id = uuid7()

    with pytest.raises(DomainValidationError, match="rating must be between 1 and 5"):
        ReviewDomain(
            user_id=user_id,
            product_id=prod_id,
            order_item_id=item_id,
            rating=0,
            created_by=user_id,
        )

    with pytest.raises(DomainValidationError, match="rating must be between 1 and 5"):
        ReviewDomain(
            user_id=user_id,
            product_id=prod_id,
            order_item_id=item_id,
            rating=6,
            created_by=user_id,
        )

    # Valid boundaries
    r1 = ReviewDomain(
        user_id=user_id,
        product_id=prod_id,
        order_item_id=item_id,
        rating=1,
        created_by=user_id,
    )
    assert r1.rating == 1

    r5 = ReviewDomain(
        user_id=user_id,
        product_id=prod_id,
        order_item_id=item_id,
        rating=5,
        created_by=user_id,
    )
    assert r5.rating == 5
