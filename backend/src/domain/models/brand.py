from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from uuid6 import uuid7

from src.domain.exceptions import DomainValidationError
from src.utils import factory_now

from .base import BaseDomain
from .product import ModerationStatus


class BrandMemberRole(StrEnum):
    REPRESENTATIVE = "representative"
    MODERATOR = "moderator"


@dataclass(slots=True, kw_only=True)
class BrandDomain(BaseDomain):
    id: UUID = field(default_factory=uuid7)
    name: str
    slug: str
    his_url: str | None = None
    logo_url: str | None = None
    is_deleted: bool = False
    views_count: int = 0
    orders_count: int = 0
    moderation_status: ModerationStatus = field(default=ModerationStatus.PENDING)
    rejection_reason: str | None = None
    is_verified: bool = False
    products_hidden_override: int | None = None
    created_at: datetime = field(default_factory=factory_now)

    def __post_init__(self) -> None:
        if (
            self.products_hidden_override is not None
            and self.products_hidden_override
            not in (
                1,
                2,
            )
        ):
            raise DomainValidationError(
                "Brand products_hidden_override must be None, 1, or 2"
            )


@dataclass(slots=True, kw_only=True)
class BrandMemberDomain(BaseDomain):
    brand_id: UUID
    user_id: UUID
    role: BrandMemberRole
    user_login: str | None = None
    created_at: datetime = field(default_factory=factory_now)
