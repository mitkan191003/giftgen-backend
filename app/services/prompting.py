from dataclasses import dataclass


@dataclass(slots=True)
class PromptRefinement:
    assistant_reply: str
    structured_prompt: str


class PromptRefiner:
    def refine(self, user_prompt: str) -> PromptRefinement:
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
        return PromptRefinement(assistant_reply=assistant_reply, structured_prompt=structured_prompt)
