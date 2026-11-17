from typing import Protocol
from uuid import UUID

from src.domain.interfaces.brand import BrandRepositoryProtocol
from src.domain.interfaces.uow import UnitOfWorkProtocol
from src.domain.models import FulfillmentStatus, QueueItemDomain


class FulfillmentQueueRepositoryProtocol(Protocol):
    async def list_self_worked_queue(
        self, user_id: UUID, status: FulfillmentStatus | None = None
    ) -> list[QueueItemDomain]: ...

    async def list_brand_queue(
        self, brand_id: UUID, status: FulfillmentStatus | None = None
    ) -> list[QueueItemDomain]: ...

    async def get_queue_item(
        self, item_id: UUID
    ) -> tuple[QueueItemDomain, UUID | None, UUID | None, UUID | None] | None: ...

    async def update_item(
        self,
        item_id: UUID,
        *,
        fulfillment_status: FulfillmentStatus | None = None,
        post_code: str | None = None,
        tracking_url: str | None = None,
        update_tracking_url: bool = False,
    ) -> QueueItemDomain: ...


class QueueUnitOfWorkProtocol(UnitOfWorkProtocol, Protocol):
    queue: FulfillmentQueueRepositoryProtocol
    brands: BrandRepositoryProtocol
