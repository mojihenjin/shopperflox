from uuid import UUID

from src.domain.exceptions import EntityNotFoundError, PermissionDeniedError
from src.domain.interfaces import AnalyticsUnitOfWorkProtocol
from src.domain.models import (
    BrandMemberRole,
    SalesAnalyticsDomain,
    UserDomain,
)


class AnalyticsService:
    def __init__(self, uow: AnalyticsUnitOfWorkProtocol) -> None:
        self.uow = uow

    async def get_my_analytics(self, actor: UserDomain) -> SalesAnalyticsDomain:
        async with self.uow:
            return await self.uow.analytics.get_self_worked_analytics(actor.id)

    async def get_brand_analytics(
        self, actor: UserDomain, brand_id: UUID
    ) -> SalesAnalyticsDomain:
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

            return await self.uow.analytics.get_brand_analytics(brand_id)
