from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from uuid6 import uuid7

from src.utils import factory_now

from .base import BaseDomain


@dataclass(slots=True, kw_only=True)
class PostOfficeDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    name: str
    country: str = field(default="Россия")
    region: str | None = field(default=None)
    city: str
    house: str
    postal_code: str
    note: str | None = field(default=None)
    is_active: bool = field(default=True)
    created_by: UUID
    created_at: datetime = field(default_factory=factory_now)
