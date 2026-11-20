from uuid import UUID

from src.domain.exceptions import EntityNotFoundError, PermissionDeniedError
from src.domain.interfaces import QueueUnitOfWorkProtocol
from src.domain.models import (
    BrandMemberRole,
    FulfillmentStatus,
    OrderStatus,
    QueueItemDomain,
    UserDomain,
)
from src.utils import resolve_tracking_url


class QueueService:
    def __init__(self, uow: QueueUnitOfWorkProtocol) -> None:
        self.uow = uow

    async def list_my_queue(
        self, actor: UserDomain, status: FulfillmentStatus | None = None
    ) -> list[QueueItemDomain]:
        async with self.uow:
            return await self.uow.queue.list_self_worked_queue(
                user_id=actor.id, status=status
            )

    async def list_brand_queue(
        self,
        actor: UserDomain,
        brand_id: UUID,
        status: FulfillmentStatus | None = None,
    ) -> list[QueueItemDomain]:
        async with self.uow:
            brand = await self.uow.brands.get_by_id(brand_id)
            if brand is None:
                raise EntityNotFoundError("Brand not found")

            has_access = "*" in actor.global_permissions
            if not has_access:
                member = await self.uow.brands.get_member(brand_id, actor.id)
                if member is not None and member.role in (
                    BrandMemberRole.REPRESENTATIVE,
                    BrandMemberRole.MODERATOR,
                    BrandMemberRole.QUEUE_MANAGER,
                ):
                    has_access = True

            if not has_access:
                raise PermissionDeniedError("Access denied")

            return await self.uow.queue.list_brand_queue(
                brand_id=brand_id, status=status
            )

    async def update_item(
        self,
        actor: UserDomain,
        item_id: UUID,
        *,
        fulfillment_status: FulfillmentStatus | None = None,
        post_code: str | None = None,
        tracking_url: str | None = None,
    ) -> QueueItemDomain:
        async with self.uow:
            res = await self.uow.queue.get_queue_item(item_id)
            if res is None:
                raise EntityNotFoundError("Order item not found")

            _item, brand_id, creator_id, created_by = res

            has_access = "*" in actor.global_permissions
            if not has_access:
                if brand_id is None:
                    # Self-worked item
                    if actor.id in (creator_id, created_by):
                        has_access = True
                else:
                    # Brand item
                    member = await self.uow.brands.get_member(brand_id, actor.id)
                    if member is not None and member.role in (
                        BrandMemberRole.REPRESENTATIVE,
                        BrandMemberRole.MODERATOR,
                        BrandMemberRole.QUEUE_MANAGER,
                    ):
                        has_access = True

            if not has_access:
                raise PermissionDeniedError("Access denied")

            update_tracking_url = False
            resolved_url = tracking_url
            if tracking_url is not None:
                update_tracking_url = True
            if post_code is not None:
                update_tracking_url = True
                if tracking_url is None or not tracking_url.strip():
                    resolved_url = resolve_tracking_url(post_code)

            updated_item = await self.uow.queue.update_item(
                item_id=item_id,
                fulfillment_status=fulfillment_status,
                post_code=post_code,
                tracking_url=resolved_url,
                update_tracking_url=update_tracking_url,
            )

            if fulfillment_status is not None:
                order = await self.uow.orders.get_by_id(
                    updated_item.order_id, for_update=True
                )
                if order is not None:
                    order_items = await self.uow.orders.list_items(order.id)
                    item_statuses = [it.fulfillment_status for it in order_items]

                    if all(s == FulfillmentStatus.DELIVERED for s in item_statuses):
                        order.transition_to(OrderStatus.DELIVERED)
                        order.passport_series = None
                        order.passport_number = None
                        await self.uow.orders.update(order)
                    elif all(s == FulfillmentStatus.RETURNED for s in item_statuses):
                        order.transition_to(OrderStatus.RETURNED)
                        order.passport_series = None
                        order.passport_number = None
                        await self.uow.orders.update(order)
                    elif any(
                        s in (FulfillmentStatus.RETURNING, FulfillmentStatus.RETURNED)
                        for s in item_statuses
                    ):
                        order.transition_to(OrderStatus.RETURNING)
                        await self.uow.orders.update(order)
                    elif all(s == FulfillmentStatus.IN_TRANSIT for s in item_statuses):
                        order.transition_to(OrderStatus.IN_TRANSIT)
                        await self.uow.orders.update(order)
                    elif all(
                        s == FulfillmentStatus.HANDED_TO_POST for s in item_statuses
                    ):
                        order.transition_to(OrderStatus.HANDED_TO_POST)
                        await self.uow.orders.update(order)
                    elif all(s == FulfillmentStatus.PACKING for s in item_statuses):
                        order.transition_to(OrderStatus.PACKING)
                        await self.uow.orders.update(order)

            await self.uow.commit()
            return updated_item
