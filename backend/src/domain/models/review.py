from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from uuid6 import uuid7

from src.domain.exceptions import DomainValidationError
from src.utils import factory_now

from .base import BaseDomain


class FitFeedback(StrEnum):
    RUNS_SMALL = "runs_small"
    TRUE_TO_SIZE = "true_to_size"
    RUNS_LARGE = "runs_large"


@dataclass(slots=True, kw_only=True)
class ReviewDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    user_id: UUID
    product_id: UUID
    rating: int
    created_by: UUID

    order_item_id: UUID | None = field(default=None)
    fit_feedback: FitFeedback | None = field(default=None)
    comment: str | None = field(default=None)
    is_published: bool = field(default=True)

    created_at: datetime = field(default_factory=factory_now)

    def __post_init__(self) -> None:
        if not (1 <= self.rating <= 5):
            raise DomainValidationError("Review rating must be between 1 and 5")
