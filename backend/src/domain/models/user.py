from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.utils import factory_now
from uuid6 import uuid7

from .base import BaseDomain


@dataclass(slots=True, kw_only=True)
class UserDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)

    login: str
    email: str | None = field(default=None)
    password_hash: str | None = field(default=None, repr=False)

    verified_profile: bool = field(default=False)
    verified_email: bool = field(default=False)

    global_permissions: list = field(default_factory=list)

    created_by: UUID | None = field(default=None)
    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)
    deleted_at: datetime | None = field(default=None)


@dataclass(slots=True, kw_only=True)
class UserPersonalDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    created_by: UUID

    firstname: str | None = field(default=None)
    lastname: str | None = field(default=None)
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


@dataclass(slots=True, kw_only=True)
class UserAddressDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    user_id: UUID
    city: str
    street: str
    postal_code: str
    created_by: UUID

    is_default: bool = field(default=False)
    created_at: datetime = field(default_factory=factory_now)

