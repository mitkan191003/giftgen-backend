from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GiftGen API"
    environment: Literal["development", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite+pysqlite:///./giftgen.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    auth_mode: Literal["development", "cognito"] = "development"
    public_share_base_url: str = "http://localhost:3000/share"

    aws_region: str = "us-east-1"
    asset_storage_mode: Literal["local", "s3"] = "local"
    asset_bucket_name: str = "giftgen-assets"
    local_asset_root: str = "./var/assets"

    modal_api_url: str | None = None
    modal_proxy_key: str | None = None
    modal_proxy_secret: str | None = None

    openai_api_key: str | None = None

    enable_job_dispatch: bool = False
    worker_poll_interval_seconds: int = 10

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
