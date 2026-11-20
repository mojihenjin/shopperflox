from typing import Protocol
from uuid import UUID

from src.domain.interfaces.brand import BrandRepositoryProtocol
from src.domain.interfaces.uow import UnitOfWorkProtocol
from src.domain.models import SalesAnalyticsDomain


class AnalyticsRepositoryProtocol(Protocol):
    async def get_self_worked_analytics(
        self, user_id: UUID
    ) -> SalesAnalyticsDomain: ...

    async def get_brand_analytics(self, brand_id: UUID) -> SalesAnalyticsDomain: ...


class AnalyticsUnitOfWorkProtocol(UnitOfWorkProtocol, Protocol):
    analytics: AnalyticsRepositoryProtocol
    brands: BrandRepositoryProtocol
