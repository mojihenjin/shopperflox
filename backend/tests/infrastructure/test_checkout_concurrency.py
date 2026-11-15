import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from uuid6 import uuid7

from main import app
from src.domain.models import (
    CategoryDomain,
    ProductDomain,
    ProductVariantDomain,
    UserAddressDomain,
    UserDomain,
)
from src.infrastructure.db import async_session_maker, engine
from src.infrastructure.db.models import (
    CartItemModel,
    CartModel,
    CategoryModel,
    OrderItemModel,
    OrderModel,
    PaymentModel,
    ProductModel,
    ProductVariantModel,
    UserAddressModel,
    UserModel,
)
from src.infrastructure.db.uow import (
    SqlAlchemyCatalogUnitOfWork,
    SqlAlchemyOrderUnitOfWork,
    SqlAlchemyUserUnitOfWork,
)
from src.infrastructure.security import JwtTokenProvider

pytestmark = pytest.mark.anyio


async def test_live_postgres_checkout_concurrency():
    # Dispose any stale connections from previous tests running on different event loops
    await engine.dispose()
    token_provider = JwtTokenProvider()

    # Verify PostgreSQL is reachable
    user_uow = SqlAlchemyUserUnitOfWork(session_factory=async_session_maker)
    catalog_uow = SqlAlchemyCatalogUnitOfWork(session_factory=async_session_maker)
    order_uow = SqlAlchemyOrderUnitOfWork(session_factory=async_session_maker)

    try:
        async with user_uow:
            pass
    except Exception as exc:
        pytest.skip(f"Live PostgreSQL not reachable: {exc}")

    # Setup unique IDs
    test_run_id = uuid4().hex[:12]
    creator_id = uuid7()

    # 0. Create creator user in users table
    creator = UserDomain(
        id=creator_id,
        login=f"creator_{test_run_id}",
        email=f"creator_{test_run_id}@example.com",
        password_hash="dummy_hash",
    )
    async with user_uow:
        await user_uow.users.add(creator)
        await user_uow.commit()

    # 1. Create a category
    category = CategoryDomain(
        name=f"Concurrency Cat {test_run_id}",
        slug=f"concurrency-cat-{test_run_id}",
        created_by=creator_id,
    )
    async with catalog_uow:
        await catalog_uow.categories.add(category)
        await catalog_uow.commit()

    # 2. Create a product and a variant with EXACTLY stock_quantity = 3
    product = ProductDomain(
        category_id=category.id,
        title=f"Limited Edition {test_run_id}",
        slug=f"limited-edition-{test_run_id}",
        base_price=Decimal("100.00"),
        is_published=True,
        created_by=creator_id,
    )
    async with catalog_uow:
        await catalog_uow.products.add(product)
        await catalog_uow.commit()

    variant = ProductVariantDomain(
        product_id=product.id,
        sku=f"CONCUR-{test_run_id}",
        size="M",
        color_name="Gold",
        stock_quantity=3,
        created_by=creator_id,
    )
    async with catalog_uow:
        await catalog_uow.variants.add(variant)
        await catalog_uow.commit()

    # 3. Create 10 users, each with an address, cart, and 1 item of the variant
    users: list[UserDomain] = []
    addresses: list[UserAddressDomain] = []
    tokens: list[str] = []

    for i in range(10):
        uid = uuid7()
        user = UserDomain(
            id=uid,
            login=f"concur_user_{test_run_id}_{i}",
            email=f"concur_{test_run_id}_{i}@example.com",
            password_hash="dummy_hash",
        )
        address = UserAddressDomain(
            user_id=uid,
            city="Berlin",
            street=f"Street {i}",
            postal_code="10115",
            created_by=uid,
        )
        users.append(user)
        addresses.append(address)
        tokens.append(token_provider.create_access_token(uid, []))

    async with user_uow:
        for u, a in zip(users, addresses, strict=True):
            await user_uow.users.add(u)
            await user_uow.addresses.add(a)
        await user_uow.commit()

    # Add 1 variant item to each user's cart
    async with order_uow:
        for u in users:
            cart = await order_uow.carts.get_or_create_for_user(u.id)
            await order_uow.carts.upsert_item(cart.id, variant.id, 1)
        await order_uow.commit()

    try:
        # 4. Launch 10 simultaneous checkout requests with asyncio.gather
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as ac:

            async def do_checkout(token: str, addr_id: str):
                return await ac.post(
                    "/api/v1/orders/checkout",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"address_id": addr_id},
                )

            tasks = [do_checkout(tokens[i], str(addresses[i].id)) for i in range(10)]
            responses = await asyncio.gather(*tasks)

        # 5. Assert: exactly 3 succeed (201), exactly 7 fail (422)
        statuses = [r.status_code for r in responses]
        success_count = sum(1 for s in statuses if s == 201)
        insufficient_count = sum(1 for s in statuses if s == 422)

        assert success_count == 3, (
            f"Expected 3 successful checkouts, got {success_count}. Statuses: {statuses}"
        )
        assert insufficient_count == 7, (
            f"Expected 7 failed checkouts (422), got {insufficient_count}. Statuses: {statuses}"
        )

        # 6. Verify stock_quantity in live PostgreSQL is EXACTLY 0 (never negative)
        async with catalog_uow:
            v_final = await catalog_uow.variants.get_by_id(variant.id)
            assert v_final is not None
            assert v_final.stock_quantity == 0, (
                f"Expected final stock 0, got {v_final.stock_quantity}"
            )

    finally:
        # Cleanup created test entities in live database (respecting FK dependency order)
        async with async_session_maker() as session:
            from sqlalchemy import delete

            user_ids = [creator_id] + [u.id for u in users]
            # 1. Order items and payments
            await session.execute(
                delete(OrderItemModel).where(OrderItemModel.variant_id == variant.id)
            )
            await session.execute(
                delete(PaymentModel).where(
                    PaymentModel.order_id.in_(
                        select(OrderModel.id).where(OrderModel.user_id.in_(user_ids))
                    )
                )
            )
            # 2. Orders
            await session.execute(
                delete(OrderModel).where(OrderModel.user_id.in_(user_ids))
            )
            # 3. Cart items and carts
            await session.execute(
                delete(CartItemModel).where(CartItemModel.variant_id == variant.id)
            )
            await session.execute(
                delete(CartModel).where(CartModel.user_id.in_(user_ids))
            )
            # 4. Product variants, products and categories
            await session.execute(
                delete(ProductVariantModel).where(ProductVariantModel.id == variant.id)
            )
            await session.execute(
                delete(ProductModel).where(ProductModel.id == product.id)
            )
            await session.execute(
                delete(CategoryModel).where(CategoryModel.id == category.id)
            )
            # 5. User addresses and users
            await session.execute(
                delete(UserAddressModel).where(UserAddressModel.user_id.in_(user_ids))
            )
            await session.execute(delete(UserModel).where(UserModel.id.in_(user_ids)))
            await session.commit()
        await engine.dispose()
