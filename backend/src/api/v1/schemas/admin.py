from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.api.v1.schemas.brand import BrandMemberResponse
from src.domain.models import FitFeedback, ModerationStatus


class AdminUserBanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reason: str
    ended_at: datetime | None = None


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    login: str
    email: str | None = None
    verified_profile: bool = False
    verified_email: bool = False
    global_permissions: list[str] = []
    is_deleted: bool = False
    deleted_at: datetime | None = None
    active_ban: AdminUserBanResponse | None = None
    created_at: datetime


class AdminUserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    login: str | None = Field(default=None, min_length=1, max_length=64)
    global_permissions: list[str] | None = None
    verified_profile: bool | None = None


class AdminBanUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(min_length=1, max_length=500)
    ended_at: datetime | None = None


class AdminBrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None = None
    logo_url: str | None = None
    his_url: str | None = None
    moderation_status: ModerationStatus = ModerationStatus.PENDING
    rejection_reason: str | None = None
    is_verified: bool = False
    views_count: int = 0
    orders_count: int = 0
    is_deleted: bool = False
    created_at: datetime
    members: list[BrandMemberResponse] = []


class AdminHideProductsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    updated_count: int


class AdminCategoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=100)
    parent_id: UUID | None = None
    sort_order: int = 0


class AdminCategoryUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=100)
    parent_id: UUID | None = None
    sort_order: int | None = None


class AdminReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    product_id: UUID
    rating: int
    comment: str | None = None
    fit_feedback: FitFeedback | None = None
    is_published: bool
    user_login: str
    product_title: str
    product_slug: str
    created_at: datetime
