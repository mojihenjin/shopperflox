from typing import Protocol
from uuid import UUID

from src.domain.interfaces.uow import UnitOfWorkProtocol
from src.domain.interfaces.user import UserRepositoryProtocol
from src.domain.models import NotificationDomain


class NotificationRepositoryProtocol(Protocol):
    async def create(self, notification: NotificationDomain) -> NotificationDomain: ...

    async def list_by_user(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[NotificationDomain], int]: ...

    async def count_unread(self, user_id: UUID) -> int: ...

    async def mark_as_read(
        self, notification_id: UUID, user_id: UUID
    ) -> NotificationDomain | None: ...

    async def mark_all_as_read(self, user_id: UUID) -> int: ...


class NotificationUnitOfWorkProtocol(UnitOfWorkProtocol, Protocol):
    notifications: NotificationRepositoryProtocol
    users: UserRepositoryProtocol
