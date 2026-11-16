from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BanUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(min_length=3, max_length=500)
    ended_at: datetime | None = None


class SetPermissionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    permissions: list[str] = Field(default_factory=list)


class UserBanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    reason: str
    created_at: datetime
    ended_at: datetime | None = None
    created_by: UUID


class RejectProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str | None = Field(default=None, max_length=1000)


class PendingCountResponse(BaseModel):
    pending_count: int
