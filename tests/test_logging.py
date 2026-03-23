from __future__ import annotations

from app.observability.logging import ContextLoggerAdapter


def test_context_logger_adapter_merges_callsite_extra() -> None:
    adapter = ContextLoggerAdapter(__import__("logging").getLogger("giftgen.test"), {"service": "giftgen-worker"})

    _, kwargs = adapter.process("message", {"extra": {"creation_id": "creation-123", "job_id": "job-456"}})

    assert kwargs["extra"] == {
        "service": "giftgen-worker",
        "creation_id": "creation-123",
        "job_id": "job-456",
    }
