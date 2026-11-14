from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_title: str = "ShopperFlox"
    version: str = "0.1.0"
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

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="UTF-8", extra="ignore"
    )
