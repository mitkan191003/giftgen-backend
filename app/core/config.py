import json
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
    database_endpoint: str | None = None
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
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                decoded = json.loads(stripped)
                if not isinstance(decoded, list):
                    raise ValueError("CORS_ORIGINS JSON value must decode to a list")
                return [str(origin).strip() for origin in decoded if str(origin).strip()]
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def resolve_runtime_secrets(self) -> "Settings":
        from app.services.aws_secrets import get_secret_payload

        if self.database_secret_id and self.database_url.startswith("sqlite"):
            payload = get_secret_payload(self.database_secret_id, self.aws_region)
            username = self._require_secret_value(
                payload,
                ("username", "user", "master_username"),
                secret_id=self.database_secret_id,
                field_name="username",
            )
            password = self._require_secret_value(
                payload,
                ("password", "master_password"),
                secret_id=self.database_secret_id,
                field_name="password",
            )
            host = self._optional_secret_value(payload, ("host", "hostname", "endpoint")) or self.database_endpoint
            if not host:
                raise RuntimeError(
                    "Database secret did not contain a host value and DATABASE_ENDPOINT was not provided "
                    f"for secret {self.database_secret_id}. Available keys: {sorted(payload.keys())}"
                )

            port_value = self._optional_secret_value(payload, ("port",), default="5432")
            port = int(port_value)
            dbname = self._optional_secret_value(
                payload,
                ("dbname", "database", "database_name", "dbName"),
                default=self.database_name,
            )
            self.database_url = (
                "postgresql+psycopg://"
                f"{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/{quote_plus(dbname)}"
            )

        if self.modal_secret_id and not self.modal_api_url:
            payload = get_secret_payload(self.modal_secret_id, self.aws_region)
            self.modal_api_url = self._require_secret_value(
                payload,
                ("modal_api_url", "api_url", "url"),
                secret_id=self.modal_secret_id,
                field_name="modal_api_url",
            )
            self.modal_proxy_key = self._optional_secret_value(
                payload,
                ("modal_proxy_key", "proxy_key"),
            )
            self.modal_proxy_secret = self._optional_secret_value(
                payload,
                ("modal_proxy_secret", "proxy_secret"),
            )

        if self.openai_secret_id and not self.openai_api_key:
            payload = get_secret_payload(self.openai_secret_id, self.aws_region)
            self.openai_api_key = self._require_secret_value(
                payload,
                ("api_key", "openai_api_key"),
                secret_id=self.openai_secret_id,
                field_name="api_key",
            )

        return self

    @staticmethod
    def _optional_secret_value(
        payload: dict[str, object],
        field_names: tuple[str, ...],
        default: str | None = None,
    ) -> str | None:
        for field_name in field_names:
            value = payload.get(field_name)
            if value is None:
                continue
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
                continue
            return str(value)
        return default

    @classmethod
    def _require_secret_value(
        cls,
        payload: dict[str, object],
        field_names: tuple[str, ...],
        *,
        secret_id: str,
        field_name: str,
    ) -> str:
        value = cls._optional_secret_value(payload, field_names)
        if value:
            return value

        raise RuntimeError(
            f"Secret {secret_id} did not contain a usable {field_name}. Available keys: {sorted(payload.keys())}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
