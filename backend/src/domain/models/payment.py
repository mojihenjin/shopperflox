from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from uuid6 import uuid7

from src.domain.exceptions import DomainValidationError, InvalidStateTransitionError
from src.utils import factory_now

from .base import BaseDomain


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


ALLOWED_PAYMENT_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.PENDING: {PaymentStatus.SUCCEEDED, PaymentStatus.FAILED},
    PaymentStatus.SUCCEEDED: {PaymentStatus.REFUNDED},
    PaymentStatus.FAILED: set(),
    PaymentStatus.REFUNDED: set(),
}


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

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise DomainValidationError("Payment amount must be non-negative")

    def transition_to(self, new_status: PaymentStatus) -> None:
        allowed = ALLOWED_PAYMENT_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition payment from {self.status} to {new_status}"
            )
        self.status = new_status
        if new_status == PaymentStatus.SUCCEEDED and self.paid_at is None:
            self.paid_at = factory_now()
