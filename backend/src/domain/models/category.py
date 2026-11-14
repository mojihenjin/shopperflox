from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from uuid6 import uuid7

from src.utils import factory_now

from .base import BaseDomain


@dataclass(slots=True, kw_only=True)
class CategoryDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    name: str
    slug: str
    created_by: UUID

    parent_id: UUID | None = field(default=None)
    sort_order: int = field(default=0)
    created_at: datetime = field(default_factory=factory_now)

