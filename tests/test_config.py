from __future__ import annotations

from sqlalchemy.engine import make_url

import app.services.aws_secrets as aws_secrets
from app.core.config import Settings


def clear_settings_env(monkeypatch) -> None:
    for key in (
        "DATABASE_URL",
        "DATABASE_NAME",
        "DATABASE_SECRET_ID",
        "DATABASE_ENDPOINT",
        "CORS_ORIGINS",
        "AUTH_MODE",
        "AWS_REGION",
        "ASSET_STORAGE_MODE",
        "ASSET_BUCKET_NAME",
        "MODAL_API_URL",
        "MODAL_PROXY_KEY",
        "MODAL_PROXY_SECRET",
        "MODAL_SECRET_ID",
        "OPENAI_API_KEY",
        "OPENAI_SECRET_ID",
    ):
        monkeypatch.delenv(key, raising=False)


def test_settings_split_comma_delimited_cors_origins(monkeypatch) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv("CORS_ORIGINS", "https://dev.giftgen.mithrak.com, https://giftgen.mithrak.com")

    settings = Settings()

    assert settings.cors_origins == [
        "https://dev.giftgen.mithrak.com",
        "https://giftgen.mithrak.com",
    ]


def test_settings_parse_json_cors_origins(monkeypatch) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv("CORS_ORIGINS", '["https://dev.giftgen.mithrak.com"]')

    settings = Settings()

    assert settings.cors_origins == ["https://dev.giftgen.mithrak.com"]


def test_settings_build_database_url_from_secret_and_endpoint_fallback(monkeypatch) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_SECRET_ID", "db-secret")
    monkeypatch.setenv("DATABASE_ENDPOINT", "giftgen-dev-postgres.abc123.us-east-1.rds.amazonaws.com")
    monkeypatch.setenv("DATABASE_NAME", "giftgen")

    def fake_get_secret_payload(secret_id: str, region_name: str) -> dict[str, object]:
        assert secret_id == "db-secret"
        assert region_name == "us-east-1"
        return {
            "username": "giftgen_admin",
            "password": "super-secret",
            "port": 5432,
        }

    monkeypatch.setattr(aws_secrets, "get_secret_payload", fake_get_secret_payload)

    settings = Settings()

    assert (
        settings.database_url
        == "postgresql+psycopg://giftgen_admin:super-secret@"
        "giftgen-dev-postgres.abc123.us-east-1.rds.amazonaws.com:5432/giftgen"
    )


def test_settings_build_database_url_from_endpoint_with_embedded_port(monkeypatch) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_SECRET_ID", "db-secret")
    monkeypatch.setenv("DATABASE_ENDPOINT", "giftgen-dev-postgres.abc123.us-east-1.rds.amazonaws.com:5432")
    monkeypatch.setenv("DATABASE_NAME", "giftgen")

    def fake_get_secret_payload(secret_id: str, region_name: str) -> dict[str, object]:
        assert secret_id == "db-secret"
        assert region_name == "us-east-1"
        return {
            "username": "giftgen",
            "password": "super-secret",
            "port": 5432,
        }

    monkeypatch.setattr(aws_secrets, "get_secret_payload", fake_get_secret_payload)

    settings = Settings()

    assert (
        settings.database_url
        == "postgresql+psycopg://giftgen:super-secret@"
        "giftgen-dev-postgres.abc123.us-east-1.rds.amazonaws.com:5432/giftgen"
    )


def test_settings_database_url_with_special_characters_is_sqlalchemy_parseable(monkeypatch) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_SECRET_ID", "db-secret")
    monkeypatch.setenv("DATABASE_ENDPOINT", "giftgen-dev-postgres.abc123.us-east-1.rds.amazonaws.com")
    monkeypatch.setenv("DATABASE_NAME", "giftgen")

    def fake_get_secret_payload(secret_id: str, region_name: str) -> dict[str, object]:
        return {
            "username": "giftgen",
            "password": ".I3Hjw7:mbCXY9TR.6C~-7X$F~FS",
            "port": 5432,
        }

    monkeypatch.setattr(aws_secrets, "get_secret_payload", fake_get_secret_payload)

    settings = Settings()
    parsed = make_url(settings.database_url)

    assert parsed.username == "giftgen"
    assert parsed.password == ".I3Hjw7:mbCXY9TR.6C~-7X$F~FS"
    assert parsed.host == "giftgen-dev-postgres.abc123.us-east-1.rds.amazonaws.com"
    assert parsed.port == 5432


def test_settings_error_when_database_host_missing_everywhere(monkeypatch) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv("DATABASE_SECRET_ID", "db-secret")

    def fake_get_secret_payload(secret_id: str, region_name: str) -> dict[str, object]:
        return {
            "username": "giftgen_admin",
            "password": "super-secret",
        }

    monkeypatch.setattr(aws_secrets, "get_secret_payload", fake_get_secret_payload)

    try:
        Settings()
    except RuntimeError as exc:
        assert "DATABASE_ENDPOINT was not provided" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Settings() should have failed when the database host was unavailable")


def test_settings_accepts_modal_and_openai_secret_aliases(monkeypatch) -> None:
    clear_settings_env(monkeypatch)
    monkeypatch.setenv("MODAL_SECRET_ID", "modal-secret")
    monkeypatch.setenv("OPENAI_SECRET_ID", "openai-secret")

    def fake_get_secret_payload(secret_id: str, region_name: str) -> dict[str, object]:
        if secret_id == "modal-secret":
            return {
                "url": "https://example.modal.run",
                "proxy_key": "proxy-key",
                "proxy_secret": "proxy-secret",
            }
        if secret_id == "openai-secret":
            return {
                "openai_api_key": "sk-test",
            }
        raise AssertionError(f"Unexpected secret lookup: {secret_id}")

    monkeypatch.setattr(aws_secrets, "get_secret_payload", fake_get_secret_payload)

    settings = Settings()

    assert settings.modal_api_url == "https://example.modal.run"
    assert settings.modal_proxy_key == "proxy-key"
    assert settings.modal_proxy_secret == "proxy-secret"
    assert settings.openai_api_key == "sk-test"
