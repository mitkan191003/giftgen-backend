from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.observability.context import get_request_id, get_user_id

_STANDARD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = get_request_id()
        if request_id:
            payload["request_id"] = request_id

        user_id = get_user_id()
        if user_id:
            payload["user_id"] = user_id

        metric_payload = getattr(record, "metric_payload", None)
        if isinstance(metric_payload, dict):
            payload.update(metric_payload)

        for key, value in record.__dict__.items():
            if key.startswith("_") or key in _STANDARD_FIELDS or key == "metric_payload":
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class ContextLoggerAdapter(logging.LoggerAdapter[Any]):
    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        merged_extra = dict(self.extra)
        call_extra = kwargs.get("extra")
        if isinstance(call_extra, dict):
            merged_extra.update(call_extra)
        kwargs["extra"] = merged_extra
        return msg, kwargs


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(handler)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(level)


def get_logger(name: str) -> logging.LoggerAdapter[Any]:
    settings = get_settings()
    return ContextLoggerAdapter(logging.getLogger(name), {"service": settings.service_name})
