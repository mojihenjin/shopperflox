from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from src.domain.models import BrandDomain, BrandMemberDomain, BrandMemberRole

from .uow import UnitOfWorkProtocol

if TYPE_CHECKING:
    from src.domain.interfaces.catalog import ProductRepositoryProtocol
    from src.domain.interfaces.user import UserRepositoryProtocol


class BrandRepositoryProtocol(Protocol):
    async def get_by_id(self, brand_id: UUID) -> BrandDomain | None: ...

    async def get_by_slug(self, slug: str) -> BrandDomain | None: ...

    async def get_by_name(self, name: str) -> BrandDomain | None: ...

    async def list_active(
        self, limit: int = 100, offset: int = 0
    ) -> list[BrandDomain]: ...

    async def list_pending(
        self, limit: int = 100, offset: int = 0
    ) -> list[BrandDomain]: ...

    async def count_pending(self) -> int: ...

    async def increment_views(self, brand_id: UUID) -> None: ...

    async def increment_orders(self, brand_id: UUID, quantity: int) -> None: ...

    async def list_by_user_id(
        self, user_id: UUID
    ) -> list[tuple[BrandDomain, BrandMemberRole]]: ...

    async def add(self, brand: BrandDomain) -> None: ...

    async def update(self, brand: BrandDomain) -> None: ...

    async def add_member(self, member: BrandMemberDomain) -> None: ...

    async def update_member(self, member: BrandMemberDomain) -> None: ...

    async def remove_member(self, brand_id: UUID, user_id: UUID) -> None: ...

    async def get_member(
        self, brand_id: UUID, user_id: UUID
    ) -> BrandMemberDomain | None: ...

    async def list_members(self, brand_id: UUID) -> list[BrandMemberDomain]: ...

    async def count_representatives(self, brand_id: UUID) -> int: ...


class BrandUnitOfWorkProtocol(UnitOfWorkProtocol, Protocol):
    brands: BrandRepositoryProtocol
    users: "UserRepositoryProtocol"
    products: "ProductRepositoryProtocol"
