from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.models import (
    UserAddressDomain,
    UserBanDomain,
    UserDomain,
    UserPersonalDomain,
)

from .uow import UnitOfWorkProtocol


class UserRepositoryProtocol(Protocol):
    async def get_by_id(
        self, user_id: UUID, *, include_deleted: bool = False
    ) -> UserDomain | None: ...

    async def get_by_login(self, login: str) -> UserDomain | None: ...

    async def get_by_email(self, email: str) -> UserDomain | None: ...

    async def exists_active(self, login: str, email: str | None = None) -> bool: ...

    async def add(self, user: UserDomain) -> None: ...

    async def update(self, user: UserDomain) -> None: ...


class UserPersonalRepositoryProtocol(Protocol):
    async def get_by_user_id(self, user_id: UUID) -> UserPersonalDomain | None: ...

    async def get_by_phone(self, phone_number: str) -> UserPersonalDomain | None: ...

    async def add(self, personal: UserPersonalDomain) -> None: ...

    async def update(self, personal: UserPersonalDomain) -> None: ...


class UserAddressRepositoryProtocol(Protocol):
    async def get_by_id(self, address_id: UUID) -> UserAddressDomain | None: ...

    async def list_by_user_id(self, user_id: UUID) -> list[UserAddressDomain]: ...

    async def get_default_by_user_id(
        self, user_id: UUID
    ) -> UserAddressDomain | None: ...

    async def unset_default_for_user(self, user_id: UUID) -> None: ...

    async def add(self, address: UserAddressDomain) -> None: ...

    async def update(self, address: UserAddressDomain) -> None: ...

    async def delete(self, address_id: UUID) -> None: ...


class UserBanRepositoryProtocol(Protocol):
    async def get_active_by_user_id(
        self, user_id: UUID, at: datetime | None = None
    ) -> UserBanDomain | None: ...

    async def list_by_user_id(self, user_id: UUID) -> list[UserBanDomain]: ...

    async def add(self, ban: UserBanDomain) -> None: ...

    async def update(self, ban: UserBanDomain) -> None: ...


class UserUnitOfWorkProtocol(UnitOfWorkProtocol, Protocol):
    users: UserRepositoryProtocol
    personal: UserPersonalRepositoryProtocol
    addresses: UserAddressRepositoryProtocol
    bans: UserBanRepositoryProtocol
