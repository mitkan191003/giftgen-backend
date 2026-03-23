from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response

from app.core.config import get_settings
from app.observability.context import clear_request_context, set_request_context
from app.observability.logging import get_logger
from app.observability.metrics import emit_metrics, MetricValue


async def request_context_middleware(request: Request, call_next) -> Response:
    settings = get_settings()
    request_id = request.headers.get(settings.request_id_header_name) or str(uuid4())
    set_request_context(request_id)

    started_at = perf_counter()
    logger = get_logger("giftgen.request")

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (perf_counter() - started_at) * 1000
        route = request.scope.get("route")
        operation = f"{request.method} {getattr(route, 'path', request.url.path)}"
        emit_metrics(
            [
                MetricValue(name="HttpRequestCount", value=1),
                MetricValue(name="HttpRequestDurationMs", value=duration_ms, unit="Milliseconds"),
            ],
            dimensions={"Operation": operation, "Outcome": "5xx"},
            properties={"path": request.url.path, "method": request.method},
        )
        logger.exception(
            "request_failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "operation": operation,
                "status_code": 500,
                "duration_ms": round(duration_ms, 2),
            },
        )
        clear_request_context()
        raise

    duration_ms = (perf_counter() - started_at) * 1000
    route = request.scope.get("route")
    operation = f"{request.method} {getattr(route, 'path', request.url.path)}"
    outcome = f"{response.status_code // 100}xx"
    response.headers[settings.request_id_header_name] = request_id

    emit_metrics(
        [
            MetricValue(name="HttpRequestCount", value=1),
            MetricValue(name="HttpRequestDurationMs", value=duration_ms, unit="Milliseconds"),
        ],
        dimensions={"Operation": operation, "Outcome": outcome},
        properties={"path": request.url.path, "method": request.method, "status_code": response.status_code},
    )
    logger.info(
        "request_completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "operation": operation,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        },
    )
    clear_request_context()
    return response
