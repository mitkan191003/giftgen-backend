from dataclasses import dataclass
import re


BLOCKED_PATTERNS = (
    "ignore previous instructions",
    "reveal the system prompt",
    "bypass safety",
    "prompt injection",
    "<script",
)

PROFANITY_MARKERS = ("fuck", "shit", "bitch")


@dataclass(slots=True)
class GuardrailResult:
    allowed: bool
    reasons: list[str]
    normalized_text: str


class PromptGuardrailService:
    def inspect(self, raw_text: str) -> GuardrailResult:
        normalized = re.sub(r"\s+", " ", raw_text).strip()
        lowered = normalized.lower()
        reasons: list[str] = []

        if len(normalized) > 2000:
            reasons.append("prompt_too_long")

        if any(pattern in lowered for pattern in BLOCKED_PATTERNS):
            reasons.append("prompt_injection_detected")

        if any(marker in lowered for marker in PROFANITY_MARKERS):
            reasons.append("profanity_detected")

        return GuardrailResult(allowed=not reasons, reasons=reasons, normalized_text=normalized)
