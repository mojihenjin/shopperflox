from dataclasses import dataclass
from uuid import UUID

from src.domain.models.user import UserDomain


@dataclass(slots=True, frozen=True)
class RegisterResultDomain:
    requires_verification: bool
    verification_token: str | None = None
    user: UserDomain | None = None

    @property
    def id(self) -> UUID | None:
        return self.user.id if self.user else None
