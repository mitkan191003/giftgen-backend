import base64
from dataclasses import dataclass
from time import perf_counter

import httpx

from app.core.config import get_settings
from app.observability import emit_metrics, get_logger
from app.observability.metrics import MetricValue


@dataclass(slots=True)
class GeneratedArtifact:
    data: bytes
    file_extension: str
    mime_type: str
    provider_job_id: str | None = None


class ModalGenerationClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = get_logger("giftgen.modal")

    def generate(self, prompt: str) -> GeneratedArtifact:
        if not self.settings.modal_api_url:
            raise RuntimeError("MODAL_API_URL is not configured")

        headers = {"Content-Type": "application/json"}
        if self.settings.modal_proxy_key:
            headers["Modal-Key"] = self.settings.modal_proxy_key
        if self.settings.modal_proxy_secret:
            headers["Modal-Secret"] = self.settings.modal_proxy_secret

        started_at = perf_counter()

        try:
            with httpx.Client(timeout=900.0, follow_redirects=True) as client:
                response = client.post(self.settings.modal_api_url, json={"prompt": prompt}, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            duration_ms = (perf_counter() - started_at) * 1000
            outcome = f"http_{exc.response.status_code}"
            emit_metrics(
                [
                    MetricValue(name="ModalRequestCount", value=1),
                    MetricValue(name="ModalRequestDurationMs", value=duration_ms, unit="Milliseconds"),
                ],
                dimensions={"Provider": "modal", "Outcome": outcome},
                properties={"status_code": exc.response.status_code},
            )
            self.logger.warning(
                "modal_request_failed",
                extra={"outcome": outcome, "status_code": exc.response.status_code, "duration_ms": round(duration_ms, 2)},
            )
            raise
        except Exception:
            duration_ms = (perf_counter() - started_at) * 1000
            emit_metrics(
                [
                    MetricValue(name="ModalRequestCount", value=1),
                    MetricValue(name="ModalRequestDurationMs", value=duration_ms, unit="Milliseconds"),
                ],
                dimensions={"Provider": "modal", "Outcome": "exception"},
            )
            self.logger.exception("modal_request_failed", extra={"outcome": "exception", "duration_ms": round(duration_ms, 2)})
            raise

        if not payload.get("success"):
            duration_ms = (perf_counter() - started_at) * 1000
            emit_metrics(
                [
                    MetricValue(name="ModalRequestCount", value=1),
                    MetricValue(name="ModalRequestDurationMs", value=duration_ms, unit="Milliseconds"),
                ],
                dimensions={"Provider": "modal", "Outcome": "provider_failure"},
            )
            self.logger.warning("modal_request_failed", extra={"outcome": "provider_failure", "duration_ms": round(duration_ms, 2)})
            raise RuntimeError(payload.get("message") or "Modal generation failed")

        model_data = payload.get("model_data")
        if not model_data:
            duration_ms = (perf_counter() - started_at) * 1000
            emit_metrics(
                [
                    MetricValue(name="ModalRequestCount", value=1),
                    MetricValue(name="ModalRequestDurationMs", value=duration_ms, unit="Milliseconds"),
                ],
                dimensions={"Provider": "modal", "Outcome": "invalid_payload"},
            )
            self.logger.warning("modal_request_failed", extra={"outcome": "invalid_payload", "duration_ms": round(duration_ms, 2)})
            raise RuntimeError("Modal response did not include model_data")

        file_extension = payload.get("format", "glb")
        mime_type = "model/gltf-binary" if file_extension == "glb" else "application/octet-stream"
        provider_job_id = (
            payload.get("provider_job_id")
            or payload.get("job_id")
            or payload.get("request_id")
            or payload.get("id")
        )
        duration_ms = (perf_counter() - started_at) * 1000
        emit_metrics(
            [
                MetricValue(name="ModalRequestCount", value=1),
                MetricValue(name="ModalRequestDurationMs", value=duration_ms, unit="Milliseconds"),
            ],
            dimensions={"Provider": "modal", "Outcome": "success"},
            properties={"provider_job_id": provider_job_id},
        )
        self.logger.info(
            "modal_request_succeeded",
            extra={"duration_ms": round(duration_ms, 2), "provider_job_id": provider_job_id, "format": file_extension},
        )
        return GeneratedArtifact(
            data=base64.b64decode(model_data),
            file_extension=file_extension,
            mime_type=mime_type,
            provider_job_id=str(provider_job_id) if provider_job_id else None,
        )
