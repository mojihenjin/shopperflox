from decimal import Decimal

import pytest
from uuid6 import uuid7

from src.application.services import CartService
from src.domain.exceptions import DomainValidationError, EntityNotFoundError
from src.domain.models import ProductDomain, ProductVariantDomain

pytestmark = pytest.mark.anyio


async def test_cart_service_flow(cart_uow):
    service = CartService(uow=cart_uow)
    user_id = uuid7()
    category_id = uuid7()

    # Create product and variant
    product = ProductDomain(
        category_id=category_id,
        title="Sneakers",
        slug="sneakers",
        base_price=Decimal("100.00"),
        is_published=True,
        created_by=user_id,
    )
    await cart_uow.products.add(product)

    variant = ProductVariantDomain(
        product_id=product.id,
        sku="SNK-42",
        size="42",
        color_name="Black",
        stock_quantity=5,
        price_override=Decimal("90.00"),
        created_by=user_id,
    )
    await cart_uow.variants.add(variant)

    # 1. Add item to cart
    item = await service.add_or_update_item(
        user_id=user_id, variant_id=variant.id, quantity=2
    )
    assert item is not None
    assert item.quantity == 2

    # 2. Exceeding quantity raises DomainValidationError
    with pytest.raises(DomainValidationError, match="exceeds available stock"):
        await service.add_or_update_item(
            user_id=user_id, variant_id=variant.id, quantity=10
        )

    # 3. Get cart
    cart, details, total = await service.get_cart(user_id)
    assert len(details) == 1
    assert details[0].unit_price == Decimal("90.00")
    assert details[0].total_price == Decimal("180.00")
    assert total == Decimal("180.00")

    # 4. Remove item
    await service.remove_item(user_id, variant.id)
    _, details_after, total_after = await service.get_cart(user_id)
    assert len(details_after) == 0
    assert total_after == Decimal("0.00")

    # 5. Non-existent variant raises EntityNotFoundError
    with pytest.raises(EntityNotFoundError):
        await service.add_or_update_item(
            user_id=user_id, variant_id=uuid7(), quantity=1
        )
