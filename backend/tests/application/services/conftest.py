from datetime import datetime
from types import TracebackType
from typing import Any, Self
from uuid import UUID

import pytest
from uuid6 import uuid7

from src.domain.exceptions import AuthenticationError
from src.domain.interfaces import (
    UserAddressRepositoryProtocol,
    UserBanRepositoryProtocol,
    UserPersonalRepositoryProtocol,
    UserRepositoryProtocol,
)
from src.domain.models import (
    UserAddressDomain,
    UserBanDomain,
    UserDomain,
    UserPersonalDomain,
)


class InMemoryUserRepository:
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


class InMemoryUserPersonalRepository:
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


class InMemoryUserAddressRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, UserAddressDomain] = {}

    async def get_by_id(self, address_id: UUID) -> UserAddressDomain | None:
        return self.store.get(address_id)

    async def list_by_user_id(
        self, user_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[UserAddressDomain]:
        all_addrs = [a for a in self.store.values() if a.user_id == user_id]
        return all_addrs[offset : offset + limit]

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


class InMemoryUserBanRepository:
    def __init__(self) -> None:
        self.store: dict[UUID, UserBanDomain] = {}

    async def get_active_by_user_id(
        self, user_id: UUID, at: datetime | None = None
    ) -> UserBanDomain | None:
        for ban in self.store.values():
            if ban.user_id == user_id and ban.is_active(at=at):
                return ban
        return None

    async def list_active_by_user_id(
        self, user_id: UUID, at: datetime | None = None
    ) -> list[UserBanDomain]:
        return [
            b
            for b in self.store.values()
            if b.user_id == user_id and b.is_active(at=at)
        ]

    async def list_by_user_id(self, user_id: UUID) -> list[UserBanDomain]:
        return [b for b in self.store.values() if b.user_id == user_id]

    async def add(self, ban: UserBanDomain) -> None:
        self.store[ban.id] = ban

    async def update(self, ban: UserBanDomain) -> None:
        self.store[ban.id] = ban


class FakeUserUnitOfWork:
    def __init__(self) -> None:
        self.users: UserRepositoryProtocol = InMemoryUserRepository()
        self.personal: UserPersonalRepositoryProtocol = InMemoryUserPersonalRepository()
        self.addresses: UserAddressRepositoryProtocol = InMemoryUserAddressRepository()
        self.bans: UserBanRepositoryProtocol = InMemoryUserBanRepository()
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


class FakePasswordHasher:
    def __init__(self) -> None:
        self.verify_call_count = 0

    def hash(self, password: str) -> str:
        return f"hashed_{password}"

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        self.verify_call_count += 1
        return hashed_password == f"hashed_{plain_password}"

    async def verify_dummy(self, plain_password: str) -> None:
        self.verify_call_count += 1


class FakeTokenProvider:
    def create_access_token(self, user_id: UUID, permissions: list[str]) -> str:
        return f"access_{user_id}_{','.join(permissions)}"

    def create_refresh_token(self, user_id: UUID) -> str:
        return f"refresh_{user_id}_jti_{uuid7()}"

    def decode_token(
        self, token: str, expected_type: str | None = "access"
    ) -> dict[str, Any]:
        parts = token.split("_")
        if expected_type == "refresh":
            if not token.startswith("refresh_"):
                raise AuthenticationError("Invalid token type")
            jti = parts[3] if len(parts) > 3 else f"jti_{parts[1]}"
            return {
                "sub": parts[1],
                "type": "refresh",
                "jti": jti,
                "exp": 9999999999,
            }

        if not token.startswith("access_"):
            raise AuthenticationError("Invalid token")
        return {
            "sub": parts[1],
            "permissions": parts[2].split(",") if parts[2] else [],
            "type": "access",
        }


class FakeTokenBlacklist:
    def __init__(self) -> None:
        self.revoked_tokens: set[str] = set()

    async def is_revoked(self, jti: str) -> bool:
        return jti in self.revoked_tokens

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        self.revoked_tokens.add(jti)


@pytest.fixture
def uow():
    return FakeUserUnitOfWork()


@pytest.fixture
def hasher():
    return FakePasswordHasher()


@pytest.fixture
def blacklist():
    return FakeTokenBlacklist()


@pytest.fixture
def token_provider():
    return FakeTokenProvider()
