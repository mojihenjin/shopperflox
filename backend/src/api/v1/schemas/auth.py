from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.api.v1.schemas.users import UserResponse


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = Field(default=None, max_length=255)


class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    requires_verification: bool
    verification_token: str | None = None
    user: UserResponse | None = None


class VerificationInitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    requires_verification: bool = True
    verification_token: str


class SendEmailCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr = Field(max_length=255)


class VerifyCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    verification_token: str = Field(min_length=1)
    code: str = Field(min_length=6, max_length=16)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    refresh_token: str = Field(min_length=1)


class TokenPairResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(min_length=6, max_length=16)
