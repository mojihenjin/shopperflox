from datetime import datetime, timezone
from uuid import UUID

from uuid6 import uuid7

from src.domain.exceptions import EntityNotFoundError
from src.domain.interfaces import NotificationUnitOfWorkProtocol, TaskQueueProtocol
from src.domain.models import NotificationDomain


class NotificationService:
    def __init__(
        self,
        uow: NotificationUnitOfWorkProtocol,
        task_queue: TaskQueueProtocol | None = None,
    ) -> None:
        self._uow = uow
        self._task_queue = task_queue

    async def notify_user(
        self,
        *,
        user_id: UUID,
        title: str,
        body: str,
        link: str | None = None,
        send_email: bool = False,
    ) -> NotificationDomain:
        notification = NotificationDomain(
            id=uuid7(),
            user_id=user_id,
            title=title,
            body=body,
            link=link,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )

        async with self._uow as uow:
            created = await uow.notifications.create(notification)
            user = None
            if send_email and self._task_queue is not None:
                user = await uow.users.get_by_id(user_id)
            await uow.commit()

        if send_email and self._task_queue is not None and user is not None:
            if user.email and user.verified_email is True:
                await self._task_queue.enqueue_email(
                    to_email=user.email,
                    subject=title,
                    body_text=body,
                )

        return created

    async def list_notifications(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[NotificationDomain], int]:
        async with self._uow as uow:
            return await uow.notifications.list_by_user(
                user_id, limit=limit, offset=offset
            )

    async def get_unread_count(self, user_id: UUID) -> int:
        async with self._uow as uow:
            return await uow.notifications.count_unread(user_id)

    async def mark_read(
        self, notification_id: UUID, user_id: UUID
    ) -> NotificationDomain:
        async with self._uow as uow:
            notification = await uow.notifications.mark_as_read(
                notification_id=notification_id, user_id=user_id
            )
            if notification is None:
                raise EntityNotFoundError("Notification not found")
            await uow.commit()
            return notification

    async def mark_all_read(self, user_id: UUID) -> int:
        async with self._uow as uow:
            count = await uow.notifications.mark_all_as_read(user_id)
            await uow.commit()
            return count
