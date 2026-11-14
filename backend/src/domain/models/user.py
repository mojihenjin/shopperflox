from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.utils import factory_now
from uuid6 import uuid7

from .base import BaseDomain


@dataclass(slots=True)
class UserDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)

    login: str
    email: str | None
    password_hash: str | None = field(repr=False)

    verified_profile: bool = field(default=False)
    verified_email: bool = field(default=False)

    global_permissions: list = field(default_factory=list)

    created_by: UUID | None = field(default=None)
    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)
    deleted_at: datetime | None = field(default=None)
