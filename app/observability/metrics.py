from __future__ import annotations

import logging
from dataclasses import dataclass
from time import time
from typing import Any

from app.core.config import get_settings


@dataclass(slots=True)
class MetricValue:
    name: str
    value: int | float
    unit: str = "Count"


def emit_metric(
    name: str,
    value: int | float,
    unit: str = "Count",
    *,
    dimensions: dict[str, str] | None = None,
    properties: dict[str, Any] | None = None,
) -> None:
    emit_metrics([MetricValue(name=name, value=value, unit=unit)], dimensions=dimensions, properties=properties)


def emit_metrics(
    metrics: list[MetricValue],
    *,
    dimensions: dict[str, str] | None = None,
    properties: dict[str, Any] | None = None,
) -> None:
    if not metrics:
        return

    settings = get_settings()
    dimension_values = {
        "Environment": settings.environment,
        "Service": settings.service_name,
    }
    if dimensions:
        dimension_values.update({key: str(value) for key, value in dimensions.items() if value is not None})

    payload: dict[str, Any] = {
        "_aws": {
            "Timestamp": int(time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": settings.metric_namespace,
                    "Dimensions": [list(dimension_values.keys())],
                    "Metrics": [{"Name": metric.name, "Unit": metric.unit} for metric in metrics],
                }
            ],
        },
        **dimension_values,
    }

    for metric in metrics:
        payload[metric.name] = metric.value

    if properties:
        payload.update(properties)

    logging.getLogger("giftgen.metrics").info("embedded_metric", extra={"metric_payload": payload})
