from typing import Protocol
from uuid import UUID

from src.domain.interfaces.uow import UnitOfWorkProtocol
from src.domain.models import PostOfficeDomain


class PostOfficeRepositoryProtocol(Protocol):
    async def get_by_id(self, office_id: UUID) -> PostOfficeDomain | None: ...

    async def list_all(
        self,
        *,
        search: str | None = None,
        city: str | None = None,
        is_active: bool | None = None,
    ) -> list[PostOfficeDomain]: ...

    async def add(self, office: PostOfficeDomain) -> None: ...

    async def update(self, office: PostOfficeDomain) -> None: ...

    async def delete(self, office_id: UUID) -> None: ...


class PostOfficeUnitOfWorkProtocol(UnitOfWorkProtocol, Protocol):
    post_offices: PostOfficeRepositoryProtocol
