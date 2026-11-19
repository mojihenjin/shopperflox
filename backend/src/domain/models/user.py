from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from uuid6 import uuid7

from src.utils import factory_now

from .base import BaseDomain


@dataclass(slots=True, kw_only=True)
class UserDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)

    login: str
    email: str | None = field(default=None)
    password_hash: str | None = field(default=None, repr=False)

    verified_profile: bool = field(default=False)
    verified_email: bool = field(default=False)

    global_permissions: list[str] = field(default_factory=list)

    created_by: UUID | None = field(default=None)
    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)
    deleted_at: datetime | None = field(default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


@dataclass(slots=True, kw_only=True)
class UserPersonalDomain(BaseDomain):
    id: UUID
    created_by: UUID

    firstname: str | None = field(default=None)
    lastname: str | None = field(default=None)
    middlename: str | None = field(default=None)
    phone_number: str | None = field(default=None)

    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)


@dataclass(slots=True, kw_only=True)
class UserBanDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    user_id: UUID
    reason: str
    created_by: UUID

    created_at: datetime = field(default_factory=factory_now)
    ended_at: datetime | None = field(default=None)

    def is_active(self, at: datetime | None = None) -> bool:
        check_time = at or factory_now()
        return self.ended_at is None or self.ended_at > check_time


@dataclass(slots=True, kw_only=True)
class UserAddressDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    user_id: UUID
    country: str = field(default="Россия")
    region: str | None = field(default=None)
    city: str
    house: str = field(default="")
    apartment: str | None = field(default=None)
    postal_code: str
    street: str | None = field(default=None)
    created_by: UUID

    is_default: bool = field(default=False)
    created_at: datetime = field(default_factory=factory_now)

    def __post_init__(self) -> None:
        if not self.house and self.street:
            self.house = self.street
        elif not self.street and self.house:
            self.street = f"{self.city}, {self.house}"
