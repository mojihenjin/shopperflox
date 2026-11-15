from decimal import Decimal

import pytest
from uuid6 import uuid7

from src.application.services import OrderService
from src.domain.exceptions import (
    PermissionDeniedError,
)
from src.domain.models import (
    OrderStatus,
    PaymentStatus,
    ProductDomain,
    ProductVariantDomain,
    UserAddressDomain,
    UserDomain,
)

pytestmark = pytest.mark.anyio


async def test_order_service_checkout_and_cancel_flow(order_uow):
    service = OrderService(uow=order_uow)
    user_id = uuid7()
    user = UserDomain(id=user_id, login="buyer")

    # 1. Setup address
    address = UserAddressDomain(
        user_id=user_id,
        city="Berlin",
        street="Alexanderplatz 1",
        postal_code="10178",
        created_by=user_id,
    )
    await order_uow.addresses.add(address)

    # 2. Setup product & variant with stock=5
    product = ProductDomain(
        category_id=uuid7(),
        title="Hoodie",
        slug="hoodie",
        base_price=Decimal("50.00"),
        is_published=True,
        created_by=user_id,
    )
    await order_uow.products.add(product)

    variant = ProductVariantDomain(
        product_id=product.id,
        sku="HD-L",
        size="L",
        color_name="Gray",
        stock_quantity=5,
        created_by=user_id,
    )
    await order_uow.variants.add(variant)

    # 3. Setup cart with 3 items
    cart = await order_uow.carts.get_or_create_for_user(user_id)
    await order_uow.carts.upsert_item(cart.id, variant.id, 3)

    # 4. Checkout
    order, items, payment, _ = await service.checkout(
        user_id=user_id,
        address_id=address.id,
        comment="Leave at door",
    )
    assert len(items) == 1
    assert items[0].quantity == 3
    assert order.status == OrderStatus.PENDING_PAYMENT
    assert order.total_amount == Decimal("150.00")
    assert order.shipping_address["city"] == "Berlin"
    assert payment.amount == Decimal("150.00")
    assert payment.status == PaymentStatus.PENDING

    # Stock must have decreased to 2
    updated_variant = await order_uow.variants.get_by_id(variant.id)
    assert updated_variant.stock_quantity == 2

    # Cart must be cleared
    cart_items = await order_uow.carts.list_items(cart.id)
    assert len(cart_items) == 0

    # 5. Cancel order returns stock
    cancelled_order = await service.cancel_order(actor=user, order_id=order.id)
    assert cancelled_order.status == OrderStatus.CANCELLED

    restored_variant = await order_uow.variants.get_by_id(variant.id)
    assert restored_variant.stock_quantity == 5


async def test_order_service_forbidden_cancel(order_uow):
    service = OrderService(uow=order_uow)
    user_id = uuid7()
    other_user = UserDomain(id=uuid7(), login="stranger")

    address = UserAddressDomain(
        user_id=user_id,
        city="Berlin",
        street="Street 1",
        postal_code="10178",
        created_by=user_id,
    )
    await order_uow.addresses.add(address)

    product = ProductDomain(
        category_id=uuid7(),
        title="Shirt",
        slug="shirt",
        base_price=Decimal("30.00"),
        is_published=True,
        created_by=user_id,
    )
    await order_uow.products.add(product)

    variant = ProductVariantDomain(
        product_id=product.id,
        sku="SH-M",
        size="M",
        color_name="Blue",
        stock_quantity=10,
        created_by=user_id,
    )
    await order_uow.variants.add(variant)

    cart = await order_uow.carts.get_or_create_for_user(user_id)
    await order_uow.carts.upsert_item(cart.id, variant.id, 1)

    order, _, _, _ = await service.checkout(user_id=user_id, address_id=address.id)

    # Stranger cannot cancel
    with pytest.raises(PermissionDeniedError):
        await service.cancel_order(actor=other_user, order_id=order.id)
