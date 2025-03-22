from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import quote_plus

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GiftGen API"
    environment: Literal["development", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite+pysqlite:///./giftgen.db"
    database_name: str = "giftgen"
    database_secret_id: str | None = None
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:3000"])

    auth_mode: Literal["development", "cognito"] = "development"
    cognito_region: str | None = None
    cognito_user_pool_id: str | None = None
    cognito_client_id: str | None = None
    cognito_domain: str | None = None
    cognito_issuer: str | None = None
    public_share_base_url: str = "http://localhost:3000/share"

    aws_region: str = "us-east-1"
    asset_storage_mode: Literal["local", "s3"] = "local"
    asset_bucket_name: str = "giftgen-assets"
    local_asset_root: str = "./var/assets"

    modal_api_url: str | None = None
    modal_proxy_key: str | None = None
    modal_proxy_secret: str | None = None
    modal_secret_id: str | None = None

    openai_api_key: str | None = None
    openai_secret_id: str | None = None

    enable_job_dispatch: bool = False
    worker_poll_interval_seconds: int = 10
    cleanup_retention_days: int = 7

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def resolve_runtime_secrets(self) -> "Settings":
        from app.services.aws_secrets import get_secret_payload

        if self.database_secret_id and self.database_url.startswith("sqlite"):
            payload = get_secret_payload(self.database_secret_id, self.aws_region)
            username = str(payload["username"])
            password = str(payload["password"])
            host = str(payload["host"])
            port = int(payload.get("port", 5432))
            dbname = str(payload.get("dbname") or self.database_name)
            self.database_url = (
                "postgresql+psycopg://"
                f"{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/{quote_plus(dbname)}"
            )

        if self.modal_secret_id and not self.modal_api_url:
            payload = get_secret_payload(self.modal_secret_id, self.aws_region)
            self.modal_api_url = str(payload["modal_api_url"])
            self.modal_proxy_key = str(payload["modal_proxy_key"]) if payload.get("modal_proxy_key") else None
            self.modal_proxy_secret = (
                str(payload["modal_proxy_secret"]) if payload.get("modal_proxy_secret") else None
            )

        if self.openai_secret_id and not self.openai_api_key:
            payload = get_secret_payload(self.openai_secret_id, self.aws_region)
            self.openai_api_key = str(payload["api_key"])

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
