from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import EntityNotFoundError
from src.domain.models import (
    FulfillmentStatus,
    QueueCustomerInfo,
    QueueItemDomain,
    QueueProductInfo,
    QueueShippingAddress,
    QueueVariantInfo,
)
from src.infrastructure.db.models import (
    OrderItemModel,
    OrderModel,
    ProductImageModel,
    ProductModel,
    ProductVariantModel,
    UserModel,
    UserPersonalModel,
)
from src.utils import factory_now


class SqlAlchemyQueueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _row_to_queue_item(
        self,
        item_model: OrderItemModel,
        order_model: OrderModel,
        user_model: UserModel,
        user_personal: UserPersonalModel | None,
        product_model: ProductModel | None,
        variant_model: ProductVariantModel | None,
        image_url: str | None,
    ) -> QueueItemDomain:
        shipping_data = order_model.shipping_address or {}
        return QueueItemDomain(
            id=item_model.id,
            order_id=item_model.order_id,
            created_at=item_model.created_at,
            updated_at=item_model.updated_at,
            product=QueueProductInfo(
                id=(
                    product_model.id
                    if product_model
                    else (variant_model.product_id if variant_model else item_model.id)
                ),
                title=(
                    product_model.title if product_model else item_model.title_snapshot
                ),
                slug=(product_model.slug if product_model else ""),
                image_url=image_url,
            ),
            variant=QueueVariantInfo(
                id=variant_model.id if variant_model else item_model.variant_id,
                sku=item_model.sku_snapshot,
                color=item_model.color_snapshot,
                size=item_model.size_snapshot,
            ),
            quantity=item_model.quantity,
            unit_price=item_model.unit_price,
            currency="RUB",
            shipping_address=QueueShippingAddress(
                city=shipping_data.get("city") or order_model.shipping_city,
                street=shipping_data.get("street")
                or shipping_data.get("house")
                or order_model.shipping_house,
                postal_code=shipping_data.get("postal_code")
                or order_model.shipping_postal_code,
                country=shipping_data.get("country") or order_model.shipping_country,
                region=shipping_data.get("region") or order_model.shipping_region,
                house=shipping_data.get("house") or order_model.shipping_house,
                apartment=shipping_data.get("apartment")
                or order_model.shipping_apartment,
            ),
            customer=QueueCustomerInfo(
                id=user_model.id,
                login=user_model.login,
                email=user_model.email,
                firstname=user_personal.firstname if user_personal else None,
                lastname=user_personal.lastname if user_personal else None,
                phone_number=user_personal.phone_number if user_personal else None,
            ),
            fulfillment_status=FulfillmentStatus(item_model.fulfillment_status),
            post_code=item_model.post_code,
            tracking_url=item_model.tracking_url,
        )

    def _base_select(self):
        return (
            select(
                OrderItemModel,
                OrderModel,
                UserModel,
                UserPersonalModel,
                ProductModel,
                ProductVariantModel,
                ProductImageModel.url.label("image_url"),
            )
            .join(OrderModel, OrderItemModel.order_id == OrderModel.id)
            .join(UserModel, OrderModel.user_id == UserModel.id)
            .outerjoin(UserPersonalModel, UserPersonalModel.id == UserModel.id)
            .outerjoin(
                ProductVariantModel,
                OrderItemModel.variant_id == ProductVariantModel.id,
            )
            .outerjoin(
                ProductModel,
                ProductVariantModel.product_id == ProductModel.id,
            )
            .outerjoin(
                ProductImageModel,
                and_(
                    ProductImageModel.product_id == ProductModel.id,
                    ProductImageModel.is_main.is_(True),
                ),
            )
        )

    async def list_self_worked_queue(
        self, user_id: UUID, status: FulfillmentStatus | None = None
    ) -> list[QueueItemDomain]:
        stmt = self._base_select().where(
            ProductModel.brand_id.is_(None),
            or_(
                ProductModel.creator_id == user_id,
                ProductModel.created_by == user_id,
            ),
        )
        if status is not None:
            stmt = stmt.where(OrderItemModel.fulfillment_status == str(status))
        stmt = stmt.order_by(OrderItemModel.created_at.desc())

        res = await self.session.execute(stmt)
        return [self._row_to_queue_item(*row) for row in res.all()]

    async def list_brand_queue(
        self, brand_id: UUID, status: FulfillmentStatus | None = None
    ) -> list[QueueItemDomain]:
        stmt = self._base_select().where(ProductModel.brand_id == brand_id)
        if status is not None:
            stmt = stmt.where(OrderItemModel.fulfillment_status == str(status))
        stmt = stmt.order_by(OrderItemModel.created_at.desc())

        res = await self.session.execute(stmt)
        return [self._row_to_queue_item(*row) for row in res.all()]

    async def get_queue_item(
        self, item_id: UUID
    ) -> tuple[QueueItemDomain, UUID | None, UUID | None, UUID | None] | None:
        stmt = self._base_select().where(OrderItemModel.id == item_id)
        res = await self.session.execute(stmt)
        row = res.first()
        if not row:
            return None
        item_m, order_m, user_m, up_m, prod_m, var_m, img_url = row
        queue_item = self._row_to_queue_item(
            item_m, order_m, user_m, up_m, prod_m, var_m, img_url
        )
        brand_id = prod_m.brand_id if prod_m else None
        creator_id = prod_m.creator_id if prod_m else None
        created_by = prod_m.created_by if prod_m else None
        return queue_item, brand_id, creator_id, created_by

    async def update_item(
        self,
        item_id: UUID,
        *,
        fulfillment_status: FulfillmentStatus | None = None,
        post_code: str | None = None,
        tracking_url: str | None = None,
        update_tracking_url: bool = False,
    ) -> QueueItemDomain:
        model = await self.session.get(OrderItemModel, item_id)
        if model is None:
            raise EntityNotFoundError("Order item not found")

        if fulfillment_status is not None:
            model.fulfillment_status = str(fulfillment_status)
        if post_code is not None:
            model.post_code = post_code
        if update_tracking_url:
            model.tracking_url = tracking_url
        model.updated_at = factory_now()
        await self.session.flush()

        res = await self.get_queue_item(item_id)
        if not res:
            raise EntityNotFoundError("Order item not found")
        return res[0]
