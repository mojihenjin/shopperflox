from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PostOfficeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    country: str = "Россия"
    region: str | None = None
    city: str
    house: str
    postal_code: str
    note: str | None = None
    is_active: bool = True
    created_by: UUID
    created_at: datetime


class PostOfficeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    country: str = Field(default="Россия", min_length=1, max_length=128)
    region: str | None = Field(default=None, max_length=128)
    city: str = Field(min_length=1, max_length=128)
    house: str = Field(min_length=1, max_length=64)
    postal_code: str = Field(min_length=1, max_length=32)
    note: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class PostOfficeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=128)
    region: str | None = Field(default=None, max_length=128)
    city: str | None = Field(default=None, max_length=128)
    house: str | None = Field(default=None, max_length=64)
    postal_code: str | None = Field(default=None, max_length=32)
    note: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
