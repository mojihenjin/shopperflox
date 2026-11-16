from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from uuid6 import uuid7

from src.utils import factory_now

from .base import BaseDomain


@dataclass(slots=True, kw_only=True)
class NotificationDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    user_id: UUID
    title: str
    body: str
    link: str | None = None
    is_read: bool = False
    created_at: datetime = field(default_factory=factory_now)
