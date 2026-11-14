from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_title: str = "ShopperFlox"
    version: str = "0.1.0"
    log_level: str = "INFO"
    log_json: bool = False

    database_url: str = (
        "postgresql+asyncpg://shopperflox:shopperflox@localhost:5432/shopperflox"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    jwt_secret_key: str = "insecure-secret-key-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="UTF-8", extra="ignore"
    )
