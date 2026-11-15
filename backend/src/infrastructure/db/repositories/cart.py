from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from src.domain.models import CartDomain, CartItemDomain
from src.infrastructure.db.models import CartItemModel, CartModel
from src.utils import factory_now


class SqlAlchemyCartRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _cart_to_domain(self, model: CartModel) -> CartDomain:
        return CartDomain(
            id=model.id,
            user_id=model.user_id,
            session_token=model.session_token,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _item_to_domain(self, model: CartItemModel) -> CartItemDomain:
        return CartItemDomain(
            id=model.id,
            cart_id=model.cart_id,
            variant_id=model.variant_id,
            quantity=model.quantity,
            created_by=model.created_by,
            created_at=model.created_at,
        )

    async def get_by_user_id(self, user_id: UUID) -> CartDomain | None:
        stmt = select(CartModel).where(CartModel.user_id == user_id)
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._cart_to_domain(model) if model else None

    async def get_or_create_for_user(self, user_id: UUID) -> CartDomain:
        cart = await self.get_by_user_id(user_id)
        if cart is not None:
            return cart

        now = factory_now()
        model = CartModel(
            id=uuid7(),
            user_id=user_id,
            session_token=None,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.session.add(model)
        await self.session.flush()
        return self._cart_to_domain(model)

    async def list_items(self, cart_id: UUID) -> list[CartItemDomain]:
        stmt = (
            select(CartItemModel)
            .where(CartItemModel.cart_id == cart_id)
            .order_by(CartItemModel.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return [self._item_to_domain(m) for m in res.scalars().all()]

    async def get_item(self, cart_id: UUID, variant_id: UUID) -> CartItemDomain | None:
        stmt = select(CartItemModel).where(
            CartItemModel.cart_id == cart_id,
            CartItemModel.variant_id == variant_id,
        )
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._item_to_domain(model) if model else None

    async def upsert_item(
        self, cart_id: UUID, variant_id: UUID, quantity: int
    ) -> CartItemDomain:
        stmt = select(CartItemModel).where(
            CartItemModel.cart_id == cart_id,
            CartItemModel.variant_id == variant_id,
        )
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        if model is None:
            model = CartItemModel(
                id=uuid7(),
                cart_id=cart_id,
                variant_id=variant_id,
                quantity=quantity,
                created_by=None,
                created_at=factory_now(),
            )
            self.session.add(model)
        else:
            model.quantity = quantity

        await self.session.flush()
        return self._item_to_domain(model)

    async def remove_item(self, cart_id: UUID, variant_id: UUID) -> None:
        stmt = delete(CartItemModel).where(
            CartItemModel.cart_id == cart_id,
            CartItemModel.variant_id == variant_id,
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def clear_cart(self, cart_id: UUID) -> None:
        stmt = delete(CartItemModel).where(CartItemModel.cart_id == cart_id)
        await self.session.execute(stmt)
        await self.session.flush()
