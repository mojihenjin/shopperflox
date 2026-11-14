from datetime import datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.domain.interfaces import (
    UnitOfWorkProtocol,
    UserAddressRepositoryProtocol,
    UserBanRepositoryProtocol,
    UserPersonalRepositoryProtocol,
    UserRepositoryProtocol,
    UserUnitOfWorkProtocol,
)
from src.domain.models import (
    UserAddressDomain,
    UserBanDomain,
    UserDomain,
    UserPersonalDomain,
)


class FakeUserRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, UserDomain] = {}

    async def get_by_id(
        self, user_id: UUID, *, include_deleted: bool = False
    ) -> UserDomain | None:
        user = self.store.get(user_id)
        if user and user.is_deleted and not include_deleted:
            return None
        return user

    async def get_by_login(self, login: str) -> UserDomain | None:
        for user in self.store.values():
            if user.login == login and not user.is_deleted:
                return user
        return None

    async def get_by_email(self, email: str) -> UserDomain | None:
        for user in self.store.values():
            if user.email == email and not user.is_deleted:
                return user
        return None

    async def exists_active(self, login: str, email: str | None = None) -> bool:
        for user in self.store.values():
            if not user.is_deleted:
                if user.login == login or (email and user.email == email):
                    return True
        return False

    async def add(self, user: UserDomain) -> None:
        self.store[user.id] = user

    async def update(self, user: UserDomain) -> None:
        self.store[user.id] = user


class FakeUserPersonalRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, UserPersonalDomain] = {}

    async def get_by_user_id(self, user_id: UUID) -> UserPersonalDomain | None:
        return self.store.get(user_id)

    async def get_by_phone(self, phone_number: str) -> UserPersonalDomain | None:
        for p in self.store.values():
            if p.phone_number == phone_number:
                return p
        return None

    async def add(self, personal: UserPersonalDomain) -> None:
        self.store[personal.id] = personal

    async def update(self, personal: UserPersonalDomain) -> None:
        self.store[personal.id] = personal


class FakeUserAddressRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, UserAddressDomain] = {}

    async def get_by_id(self, address_id: UUID) -> UserAddressDomain | None:
        return self.store.get(address_id)

    async def list_by_user_id(self, user_id: UUID) -> list[UserAddressDomain]:
        return [a for a in self.store.values() if a.user_id == user_id]

    async def get_default_by_user_id(self, user_id: UUID) -> UserAddressDomain | None:
        for a in self.store.values():
            if a.user_id == user_id and a.is_default:
                return a
        return None

    async def unset_default_for_user(self, user_id: UUID) -> None:
        for a in self.store.values():
            if a.user_id == user_id and a.is_default:
                a.is_default = False

    async def add(self, address: UserAddressDomain) -> None:
        self.store[address.id] = address

    async def update(self, address: UserAddressDomain) -> None:
        self.store[address.id] = address

    async def delete(self, address_id: UUID) -> None:
        self.store.pop(address_id, None)


class FakeUserBanRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, UserBanDomain] = {}

    async def get_active_by_user_id(
        self, user_id: UUID, at: datetime | None = None
    ) -> UserBanDomain | None:
        for ban in self.store.values():
            if ban.user_id == user_id and ban.is_active(at=at):
                return ban
        return None

    async def list_by_user_id(self, user_id: UUID) -> list[UserBanDomain]:
        return [b for b in self.store.values() if b.user_id == user_id]

    async def add(self, ban: UserBanDomain) -> None:
        self.store[ban.id] = ban

    async def update(self, ban: UserBanDomain) -> None:
        self.store[ban.id] = ban


class FakeUserUnitOfWork:
    def __init__(self) -> None:
        self.users: UserRepositoryProtocol = FakeUserRepository()
        self.personal: UserPersonalRepositoryProtocol = FakeUserPersonalRepository()
        self.addresses: UserAddressRepositoryProtocol = FakeUserAddressRepository()
        self.bans: UserBanRepositoryProtocol = FakeUserBanRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@pytest.mark.anyio
async def test_user_uow_and_repositories_execution():
    uow: UserUnitOfWorkProtocol = FakeUserUnitOfWork()

    author_id = uuid7()
    user = UserDomain(login="john", email="john@example.com")
    personal = UserPersonalDomain(id=user.id, created_by=author_id, firstname="John")
    address = UserAddressDomain(
        user_id=user.id,
        city="Berlin",
        street="Main St",
        postal_code="10115",
        created_by=author_id,
        is_default=True,
    )

    async with uow:
        assert await uow.users.exists_active("john") is False
        await uow.users.add(user)
        assert await uow.users.exists_active("john") is True

        await uow.personal.add(personal)
        fetched_personal = await uow.personal.get_by_user_id(user.id)
        assert fetched_personal is not None
        assert fetched_personal.firstname == "John"

        await uow.addresses.add(address)
        default_addr = await uow.addresses.get_default_by_user_id(user.id)
        assert default_addr is not None
        assert default_addr.is_default is True

        await uow.addresses.unset_default_for_user(user.id)
        default_after_unset = await uow.addresses.get_default_by_user_id(user.id)
        assert default_after_unset is None

        await uow.commit()

    assert uow.committed is True
    assert uow.rolled_back is False


@pytest.mark.anyio
async def test_uow_rollback_on_exception():
    uow: UnitOfWorkProtocol = FakeUserUnitOfWork()

    with pytest.raises(RuntimeError, match="DB failure"):
        async with uow:
            raise RuntimeError("DB failure")

    assert uow.rolled_back is True
    assert uow.committed is False
