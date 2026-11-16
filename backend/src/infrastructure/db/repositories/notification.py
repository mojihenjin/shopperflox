from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import NotificationDomain
from src.infrastructure.db.models import NotificationModel


class SqlAlchemyNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: NotificationModel) -> NotificationDomain:
        return NotificationDomain(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            body=model.body,
            link=model.link,
            is_read=model.is_read,
            created_at=model.created_at,
        )

    async def create(self, notification: NotificationDomain) -> NotificationDomain:
        model = NotificationModel(
            id=notification.id,
            user_id=notification.user_id,
            title=notification.title,
            body=notification.body,
            link=notification.link,
            is_read=notification.is_read,
            created_at=notification.created_at,
        )
        self.session.add(model)
        await self.session.flush()
        return self._to_domain(model)

    async def list_by_user(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[NotificationDomain], int]:
        count_stmt = select(func.count(NotificationModel.id)).where(
            NotificationModel.user_id == user_id
        )
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = (
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await self.session.execute(stmt)
        items = [self._to_domain(m) for m in res.scalars().all()]
        return items, total

    async def count_unread(self, user_id: UUID) -> int:
        stmt = select(func.count(NotificationModel.id)).where(
            NotificationModel.user_id == user_id,
            NotificationModel.is_read.is_(False),
        )
        res = await self.session.execute(stmt)
        return res.scalar() or 0

    async def mark_as_read(
        self, notification_id: UUID, user_id: UUID
    ) -> NotificationDomain | None:
        stmt = select(NotificationModel).where(
            NotificationModel.id == notification_id,
            NotificationModel.user_id == user_id,
        )
        res = await self.session.execute(stmt)
        model = res.scalar_one_or_none()
        if not model:
            return None
        if not model.is_read:
            model.is_read = True
            await self.session.flush()
        return self._to_domain(model)

    async def mark_all_as_read(self, user_id: UUID) -> int:
        stmt = (
            update(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.is_read.is_(False),
            )
            .values(is_read=True)
        )
        res = await self.session.execute(stmt)
        return res.rowcount
