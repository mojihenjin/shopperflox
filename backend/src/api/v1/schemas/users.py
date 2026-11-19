from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .catalog import ProductResponse


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    login: str
    email: str | None = None
    verified_profile: bool = False
    verified_email: bool = False
    global_permissions: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class UserPersonalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    firstname: str | None = None
    lastname: str | None = None
    middlename: str | None = None
    phone_number: str | None = None
    created_at: datetime
    updated_at: datetime


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserResponse
    personal: UserPersonalResponse | None = None


class UpdatePersonalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    firstname: str | None = Field(default=None, max_length=100)
    lastname: str | None = Field(default=None, max_length=100)
    middlename: str | None = Field(default=None, max_length=100)
    phone_number: str | None = Field(default=None, max_length=30)


class CreateAddressRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    country: str = Field(default="Россия", max_length=128)
    region: str | None = Field(default=None, max_length=128)
    city: str = Field(min_length=1, max_length=100)
    house: str = Field(default="", max_length=64)
    apartment: str | None = Field(default=None, max_length=64)
    street: str | None = Field(default=None, max_length=255)
    postal_code: str = Field(min_length=1, max_length=20)
    is_default: bool = False

    @model_validator(mode="after")
    def validate_house_or_street(self) -> Self:
        if not self.house and self.street:
            self.house = self.street
        elif not self.house and not self.street:
            raise ValueError("Поле house обязательно")
        return self


class UserAddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    country: str = "Россия"
    region: str | None = None
    city: str
    house: str = ""
    apartment: str | None = None
    street: str | None = None
    postal_code: str
    is_default: bool
    created_at: datetime


class PublicUserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    login: str
    verified_profile: bool = False
    created_at: datetime
    products: list[ProductResponse] = Field(default_factory=list)
