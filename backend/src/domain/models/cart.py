from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.utils import factory_now
from uuid6 import uuid7

from .base import BaseDomain


@dataclass(slots=True, kw_only=True)
class CartDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)

    user_id: UUID | None = field(default=None)
    session_token: str | None = field(default=None)
    created_by: UUID | None = field(default=None)

    created_at: datetime = field(default_factory=factory_now)
    updated_at: datetime = field(default_factory=factory_now)


@dataclass(slots=True, kw_only=True)
class CartItemDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    cart_id: UUID
    variant_id: UUID
    quantity: int = field(default=1)

    created_by: UUID | None = field(default=None)
    created_at: datetime = field(default_factory=factory_now)

