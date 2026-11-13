from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_title: str = "ShopperFlox"
    version: str = "0.1.0"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="UTF-8", extra="ignore"
    )
