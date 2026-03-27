from dataclasses import dataclass
from time import perf_counter

from app.observability import emit_metrics, MetricValue


@dataclass(slots=True)
class PromptRefinement:
    assistant_reply: str
    structured_prompt: str


class PromptRefiner:
    def refine(self, user_prompt: str) -> PromptRefinement:
        started_at = perf_counter()
        concise_prompt = user_prompt.strip()
        structured_prompt = (
            "Create a polished, gift-ready 3D object. "
            f"Primary concept: {concise_prompt}. "
            "Return one centered object with readable silhouette, clean materials, and no background."
        )
        assistant_reply = (
            "I tightened that into a generation-ready prompt with a single centered object, "
            "clean materials, and no scene clutter."
        )
        duration_ms = (perf_counter() - started_at) * 1000
        emit_metrics(
            [
                MetricValue(name="PromptRefinementCount", value=1),
                MetricValue(name="PromptRefinementDurationMs", value=duration_ms, unit="Milliseconds"),
                MetricValue(name="PromptRefinementCostUsd", value=0, unit="None"),
            ],
            dimensions={"Provider": "stub", "Outcome": "success"},
        )
        return PromptRefinement(assistant_reply=assistant_reply, structured_prompt=structured_prompt)
