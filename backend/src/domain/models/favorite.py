from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.utils import factory_now

from .base import BaseDomain


@dataclass(slots=True, kw_only=True)
class FavoriteDomain(BaseDomain):
    user_id: UUID
    product_id: UUID
    created_by: UUID

    created_at: datetime = field(default_factory=factory_now)

