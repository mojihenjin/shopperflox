from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.utils import factory_now
from uuid6 import uuid7

from .base import BaseDomain


@dataclass(slots=True, kw_only=True)
class ReviewDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    user_id: UUID
    product_id: UUID
    order_item_id: UUID
    rating: int
    created_by: UUID

    fit_feedback: str | None = field(default=None)
    comment: str | None = field(default=None)
    is_published: bool = field(default=True)

    created_at: datetime = field(default_factory=factory_now)


__all__ = ["ReviewDomain"]
