from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from src.domain.models import (
    FitFeedback,
    OrderDomain,
    OrderItemDomain,
    OrderStatus,
    PaymentDomain,
    PaymentStatus,
    ReviewDomain,
)
from src.infrastructure.db.models import (
    OrderItemModel,
    OrderModel,
    PaymentModel,
    ProductModel,
    ProductVariantModel,
    ReviewModel,
)


class SqlAlchemyOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _order_to_domain(self, model: OrderModel) -> OrderDomain:
        return OrderDomain(
            id=model.id,
            user_id=model.user_id,
            total_amount=model.total_amount,
            shipping_address=model.shipping_address,
            status=OrderStatus(model.status),
            tracking_number=model.tracking_number,
            post_code=model.post_code,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _item_to_domain(
        self, model: OrderItemModel, product_slug: str | None = None
    ) -> OrderItemDomain:
        return OrderItemDomain(
            id=model.id,
            order_id=model.order_id,
            variant_id=model.variant_id,
            title_snapshot=model.title_snapshot,
            sku_snapshot=model.sku_snapshot,
            size_snapshot=model.size_snapshot,
            color_snapshot=model.color_snapshot,
            unit_price=model.unit_price,
            quantity=model.quantity,
            product_slug=product_slug,
            created_by=model.created_by,
            created_at=model.created_at,
        )

    async def get_by_id(
        self, order_id: UUID, *, for_update: bool = False
    ) -> OrderDomain | None:
        stmt = select(OrderModel).where(OrderModel.id == order_id)
        if for_update:
            stmt = stmt.with_for_update()
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._order_to_domain(model) if model else None

    async def list_items(self, order_id: UUID) -> list[OrderItemDomain]:
        stmt = (
            select(OrderItemModel, ProductModel.slug)
            .outerjoin(
                ProductVariantModel,
                OrderItemModel.variant_id == ProductVariantModel.id,
            )
            .outerjoin(
                ProductModel,
                ProductVariantModel.product_id == ProductModel.id,
            )
            .where(OrderItemModel.order_id == order_id)
            .order_by(OrderItemModel.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return [
            self._item_to_domain(item_model, product_slug)
            for item_model, product_slug in res.all()
        ]

    async def list_by_user_id(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[OrderDomain], int]:
        count_stmt = select(func.count(OrderModel.id)).where(
            OrderModel.user_id == user_id
        )
        total_res = await self.session.execute(count_stmt)
        total_count = total_res.scalar() or 0

        stmt = (
            select(OrderModel)
            .where(OrderModel.user_id == user_id)
            .order_by(OrderModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        orders = [self._order_to_domain(m) for m in res.scalars().all()]
        return orders, total_count

    async def list_all(
        self,
        status: OrderStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[OrderDomain], int]:
        filters = []
        if status is not None:
            filters.append(OrderModel.status == str(status))

        count_stmt = select(func.count(OrderModel.id)).where(*filters)
        total_res = await self.session.execute(count_stmt)
        total_count = total_res.scalar() or 0

        stmt = (
            select(OrderModel)
            .where(*filters)
            .order_by(OrderModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        orders = [self._order_to_domain(m) for m in res.scalars().all()]
        return orders, total_count

    async def has_user_purchased_product(self, user_id: UUID, product_id: UUID) -> bool:
        stmt = (
            select(func.count(OrderModel.id))
            .join(OrderItemModel, OrderItemModel.order_id == OrderModel.id)
            .join(
                ProductVariantModel,
                ProductVariantModel.id == OrderItemModel.variant_id,
            )
            .where(
                OrderModel.user_id == user_id,
                OrderModel.status == OrderStatus.DELIVERED,
                ProductVariantModel.product_id == product_id,
            )
        )
        res = await self.session.execute(stmt)
        count = res.scalar() or 0
        return count > 0

    async def add(
        self, order: OrderDomain, items: list[OrderItemDomain] | None = None
    ) -> None:
        model = OrderModel(
            id=order.id,
            user_id=order.user_id,
            total_amount=order.total_amount,
            shipping_address=order.shipping_address,
            status=str(order.status),
            tracking_number=order.tracking_number,
            post_code=order.post_code,
            created_by=order.created_by,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
        self.session.add(model)

        if items:
            for item in items:
                item_model = OrderItemModel(
                    id=item.id,
                    order_id=item.order_id,
                    variant_id=item.variant_id,
                    title_snapshot=item.title_snapshot,
                    sku_snapshot=item.sku_snapshot,
                    size_snapshot=item.size_snapshot,
                    color_snapshot=item.color_snapshot,
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                    created_by=item.created_by,
                    created_at=item.created_at,
                )
                self.session.add(item_model)

        await self.session.flush()

    async def update(self, order: OrderDomain) -> None:
        model = await self.session.get(OrderModel, order.id)
        if model is None:
            raise EntityNotFoundError("Order not found")
        model.status = str(order.status)
        model.tracking_number = order.tracking_number
        model.post_code = order.post_code
        model.updated_at = order.updated_at
        await self.session.flush()


class SqlAlchemyPaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: PaymentModel) -> PaymentDomain:
        return PaymentDomain(
            id=model.id,
            order_id=model.order_id,
            provider=model.provider,
            amount=model.amount,
            external_id=model.external_id,
            status=PaymentStatus(model.status),
            created_by=model.created_by,
            created_at=model.created_at,
            paid_at=model.paid_at,
        )

    async def get_by_id(
        self, payment_id: UUID, *, for_update: bool = False
    ) -> PaymentDomain | None:
        stmt = select(PaymentModel).where(PaymentModel.id == payment_id)
        if for_update:
            stmt = stmt.with_for_update()
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_order_id(
        self, order_id: UUID, *, for_update: bool = False
    ) -> PaymentDomain | None:
        stmt = select(PaymentModel).where(PaymentModel.order_id == order_id)
        if for_update:
            stmt = stmt.with_for_update()
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_external_id(
        self, external_transaction_id: str, *, for_update: bool = False
    ) -> PaymentDomain | None:
        stmt = select(PaymentModel).where(
            PaymentModel.external_id == external_transaction_id
        )
        if for_update:
            stmt = stmt.with_for_update()
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def add(self, payment: PaymentDomain) -> None:
        model = PaymentModel(
            id=payment.id,
            order_id=payment.order_id,
            provider=payment.provider,
            amount=payment.amount,
            external_id=payment.external_id,
            status=str(payment.status),
            created_by=payment.created_by,
            created_at=payment.created_at,
            paid_at=payment.paid_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Payment for order '{payment.order_id}' or with external ID '{payment.external_id}' already exists"
            ) from exc

    async def update(self, payment: PaymentDomain) -> None:
        model = await self.session.get(PaymentModel, payment.id)
        if model is None:
            raise EntityNotFoundError("Payment not found")
        model.external_id = payment.external_id
        model.status = str(payment.status)
        model.paid_at = payment.paid_at
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Payment with external ID '{payment.external_id}' already exists"
            ) from exc


class SqlAlchemyReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: ReviewModel) -> ReviewDomain:
        return ReviewDomain(
            id=model.id,
            user_id=model.user_id,
            product_id=model.product_id,
            order_item_id=model.order_item_id,
            rating=model.rating,
            fit_feedback=(
                FitFeedback(model.fit_feedback) if model.fit_feedback else None
            ),
            comment=model.comment,
            is_published=model.is_published,
            created_by=model.created_by,
            created_at=model.created_at,
        )

    async def get_by_id(self, review_id: UUID) -> ReviewDomain | None:
        model = await self.session.get(ReviewModel, review_id)
        return self._to_domain(model) if model else None

    async def get_by_user_and_product(
        self, user_id: UUID, product_id: UUID
    ) -> ReviewDomain | None:
        stmt = select(ReviewModel).where(
            ReviewModel.user_id == user_id, ReviewModel.product_id == product_id
        )
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_by_product_id(
        self, product_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[ReviewDomain], int]:
        count_stmt = select(func.count(ReviewModel.id)).where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_published.is_(True),
        )
        total_res = await self.session.execute(count_stmt)
        total_count = total_res.scalar() or 0

        stmt = (
            select(ReviewModel)
            .where(
                ReviewModel.product_id == product_id,
                ReviewModel.is_published.is_(True),
            )
            .order_by(ReviewModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        reviews = [self._to_domain(m) for m in res.scalars().all()]
        return reviews, total_count

    async def add(self, review: ReviewDomain) -> None:
        model = ReviewModel(
            id=review.id,
            user_id=review.user_id,
            product_id=review.product_id,
            order_item_id=review.order_item_id,
            rating=review.rating,
            fit_feedback=str(review.fit_feedback) if review.fit_feedback else None,
            comment=review.comment,
            is_published=review.is_published,
            created_by=review.created_by,
            created_at=review.created_at,
        )
        self.session.add(model)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise EntityAlreadyExistsError(
                f"Review by user '{review.user_id}' for product '{review.product_id}' already exists"
            ) from exc

    async def delete(self, review_id: UUID) -> None:
        stmt = delete(ReviewModel).where(ReviewModel.id == review_id)
        await self.session.execute(stmt)
        await self.session.flush()
