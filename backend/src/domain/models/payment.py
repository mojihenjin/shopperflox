from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from src.utils import factory_now
from uuid6 import uuid7

from .base import BaseDomain


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass(slots=True, kw_only=True)
class PaymentDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    order_id: UUID
    provider: str
    amount: Decimal

    external_id: str | None = field(default=None)
    status: PaymentStatus = field(default=PaymentStatus.PENDING)
    created_by: UUID | None = field(default=None)

    created_at: datetime = field(default_factory=factory_now)
    paid_at: datetime | None = field(default=None)


__all__ = [
    "PaymentDomain",
    "PaymentStatus",
]
