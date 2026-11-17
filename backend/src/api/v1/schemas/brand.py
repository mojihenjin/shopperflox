from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BrandCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=150)
    his_url: str | None = Field(default=None, max_length=512)


class BrandUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=150)
    his_url: str | None = Field(default=None, max_length=512)


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    his_url: str | None = None
    logo_url: str | None = None
    is_deleted: bool = False
    views_count: int = 0
    orders_count: int = 0
    moderation_status: str = "pending"
    rejection_reason: str | None = None
    is_verified: bool = False
    products_hidden_override: int | None = None
    created_at: datetime


class BrandRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str | None = Field(default=None, max_length=1000)


class BrandVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    is_verified: bool


class BrandMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    brand_id: UUID
    user_id: UUID
    user_login: str | None = None
    role: str
    created_at: datetime


class MyBrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    brand: BrandResponse
    role: str


class AddBrandMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    login: str = Field(min_length=1, max_length=150)
    role: Literal["representative", "moderator", "queue_manager"]


class RemoveMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    removed: bool = True
    brand_deleted: bool = False
