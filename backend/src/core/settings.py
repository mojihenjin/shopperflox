from typing import Literal, Self

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_title: str = "ShopperFlox"
    version: str = "0.1.0"
    app_env: Literal["dev", "test", "production"] = Field(
        default="dev", validation_alias=AliasChoices("APP_ENV", "app_env")
    )
    enduro_attack: bool = Field(
        default=False, validation_alias=AliasChoices("ENDURO_ATTACK", "enduro_attack")
    )
    debug: bool = Field(default=False, validation_alias=AliasChoices("DEBUG", "debug"))
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = Field(
        default=(
            "postgresql+asyncpg://shopperflox:shopperflox@localhost:5432/shopperflox"
        ),
        validation_alias=AliasChoices("DATABASE_URL", "DB_URL", "database_url"),
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    pepper: str = Field(default="", validation_alias=AliasChoices("PEPPER", "pepper"))
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )

    jwt_algorithm: str = Field(
        default="EdDSA",
        validation_alias=AliasChoices("JWT_ALGORITHM", "jwt_algorithm"),
    )
    jwt_private_key: str = Field(
        default="",
        validation_alias=AliasChoices("JWT_PRIVATE_KEY", "jwt_private_key"),
    )
    jwt_public_key: str = Field(
        default="",
        validation_alias=AliasChoices("JWT_PUBLIC_KEY", "jwt_public_key"),
    )
    jwt_secret_key: str = Field(
        default="insecure-secret-key-change-me",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "jwt_secret_key"),
    )
    jwt_access_ttl_minutes: int = Field(
        default=15,
        validation_alias=AliasChoices(
            "JWT_ACCESS_TTL_MINUTES", "jwt_access_ttl_minutes"
        ),
    )
    jwt_refresh_ttl_days: int = Field(
        default=30,
        validation_alias=AliasChoices("JWT_REFRESH_TTL_DAYS", "jwt_refresh_ttl_days"),
    )
    webhook_secret: str = Field(
        default="dev_webhook_secret",
        validation_alias=AliasChoices("WEBHOOK_SECRET", "webhook_secret"),
    )

    # Email
    email_backend: Literal["console", "smtp"] = Field(
        default="console",
        validation_alias=AliasChoices("EMAIL_BACKEND", "email_backend"),
    )
    smtp_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("SMTP_HOST", "smtp_host"),
    )
    smtp_port: int = Field(
        default=587,
        validation_alias=AliasChoices("SMTP_PORT", "smtp_port"),
    )
    smtp_user: str = Field(
        default="",
        validation_alias=AliasChoices("SMTP_USER", "smtp_user"),
    )
    smtp_password: str = Field(
        default="",
        validation_alias=AliasChoices("SMTP_PASSWORD", "smtp_password"),
    )
    smtp_from: str = Field(
        default="noreply@shopper.flox",
        validation_alias=AliasChoices("SMTP_FROM", "smtp_from"),
    )
    smtp_use_tls: bool = Field(
        default=True,
        validation_alias=AliasChoices("SMTP_USE_TLS", "smtp_use_tls"),
    )

    # File Storage
    storage_backend: Literal["local", "s3"] = Field(
        default="local",
        validation_alias=AliasChoices("STORAGE_BACKEND", "storage_backend"),
    )
    media_local_dir: str = Field(
        default="/app/media",
        validation_alias=AliasChoices("MEDIA_LOCAL_DIR", "media_local_dir"),
    )
    media_base_url: str = Field(
        default="/media",
        validation_alias=AliasChoices("MEDIA_BASE_URL", "media_base_url"),
    )
    s3_endpoint_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_ENDPOINT_URL", "s3_endpoint_url"),
    )
    s3_bucket: str = Field(
        default="shopperflox",
        validation_alias=AliasChoices("S3_BUCKET", "s3_bucket"),
    )
    s3_access_key: str = Field(
        default="",
        validation_alias=AliasChoices("S3_ACCESS_KEY", "s3_access_key"),
    )
    s3_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices("S3_SECRET_KEY", "s3_secret_key"),
    )
    s3_region: str = Field(
        default="ru-1",
        validation_alias=AliasChoices("S3_REGION", "s3_region"),
    )

    # Payment Gateway
    payment_backend: Literal["stub"] = Field(
        default="stub",
        validation_alias=AliasChoices("PAYMENT_BACKEND", "payment_backend"),
    )
    billing_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("BILLING_ENABLED", "billing_enabled"),
    )
    billing_url: str = Field(
        default="",
        validation_alias=AliasChoices("BILLING_URL", "billing_url"),
    )

    @property
    def BILLING_ENABLED(self) -> bool:
        return self.billing_enabled

    @BILLING_ENABLED.setter
    def BILLING_ENABLED(self, value: bool) -> None:
        self.billing_enabled = value

    @property
    def BILLING_URL(self) -> str:
        return self.billing_url

    @BILLING_URL.setter
    def BILLING_URL(self, value: str) -> None:
        self.billing_url = value

    @property
    def DEBUG(self) -> bool:
        return self.debug

    @DEBUG.setter
    def DEBUG(self, value: bool) -> None:
        self.debug = value

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="UTF-8", extra="ignore"
    )

    @model_validator(mode="after")
    def validate_production_configuration(self) -> Self:
        if self.app_env == "production":
            if self.enduro_attack:
                raise ValueError(
                    "ENDURO_ATTACK mode is strictly prohibited when APP_ENV is 'production'"
                )
            if (
                not self.webhook_secret
                or self.webhook_secret == "dev_webhook_secret"
                or len(self.webhook_secret) < 32
            ):
                raise ValueError(
                    "WEBHOOK_SECRET must be at least 32 characters and cannot use default value in production"
                )
            if self.jwt_algorithm.startswith("HS"):
                if (
                    not self.jwt_secret_key
                    or self.jwt_secret_key == "insecure-secret-key-change-me"
                    or len(self.jwt_secret_key) < 32
                ):
                    raise ValueError(
                        "JWT_SECRET_KEY must be at least 32 characters and cannot use default value in production"
                    )
            else:
                if not self.jwt_private_key:
                    raise ValueError(
                        "JWT_PRIVATE_KEY must be configured in production when using asymmetric JWT algorithms"
                    )
        return self
