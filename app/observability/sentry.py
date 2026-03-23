from __future__ import annotations

import logging

from app.core.config import get_settings


def configure_sentry() -> None:
    settings = get_settings()
    if not settings.sentry_dsn:
        return

    try:
        import sentry_sdk
    except ImportError:
        logging.getLogger("giftgen.sentry").warning("sentry_sdk_not_installed")
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        enable_logs=settings.sentry_enable_logs,
    )
