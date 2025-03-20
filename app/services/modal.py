import base64
from dataclasses import dataclass

import httpx

from app.core.config import get_settings


@dataclass(slots=True)
class GeneratedArtifact:
    data: bytes
    file_extension: str
    mime_type: str
    provider_job_id: str | None = None


class ModalGenerationClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def generate(self, prompt: str) -> GeneratedArtifact:
        if not self.settings.modal_api_url:
            raise RuntimeError("MODAL_API_URL is not configured")

        headers = {"Content-Type": "application/json"}
        if self.settings.modal_proxy_key:
            headers["Modal-Key"] = self.settings.modal_proxy_key
        if self.settings.modal_proxy_secret:
            headers["Modal-Secret"] = self.settings.modal_proxy_secret

        with httpx.Client(timeout=900.0, follow_redirects=True) as client:
            response = client.post(self.settings.modal_api_url, json={"prompt": prompt}, headers=headers)
            response.raise_for_status()
            payload = response.json()

        if not payload.get("success"):
            raise RuntimeError(payload.get("message") or "Modal generation failed")

        model_data = payload.get("model_data")
        if not model_data:
            raise RuntimeError("Modal response did not include model_data")

        file_extension = payload.get("format", "glb")
        mime_type = "model/gltf-binary" if file_extension == "glb" else "application/octet-stream"
        provider_job_id = (
            payload.get("provider_job_id")
            or payload.get("job_id")
            or payload.get("request_id")
            or payload.get("id")
        )
        return GeneratedArtifact(
            data=base64.b64decode(model_data),
            file_extension=file_extension,
            mime_type=mime_type,
            provider_job_id=str(provider_job_id) if provider_job_id else None,
        )
