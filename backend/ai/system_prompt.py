"""SystemPromptManager — the one global system prompt, modeled as just
another named prompt_versions row (name="system_prompt") rather than a
standalone table. See docs/prompt-engine-architecture.md §4 for the full
reasoning: PromptRegistry already is a versioned-content/one-active-row
store, so a second table for a single global string would just duplicate
a state machine that's already built and tested, for no real benefit.

Constructor-injected with an existing PromptRegistry (not a Session) —
this class has nothing to add to "how do I get a database session,"
PromptRegistry already owns that.
"""
from typing import List

from .prompt_registry import PromptRegistry, PromptVersion

DEFAULT_SYSTEM_PROMPT = (
    "You are a research assistant for a PhD student. Help with literature "
    "review, methodology, data analysis, and academic writing. Prioritize "
    "accuracy over confidence: flag uncertainty rather than guessing, and "
    "never fabricate citations, data, or results. Cite specific sources "
    "when referencing evidence. Use clear, precise, academic language, "
    "and default to concise, well-structured answers over long prose."
)


class SystemPromptManager:
    NAME = "system_prompt"

    def __init__(self, registry: PromptRegistry):
        self.registry = registry

    def get_active_prompt(self) -> str:
        text, _version = self.registry.get_prompt(self.NAME)
        return text

    def set_active_prompt(self, content: str) -> None:
        """Creates the first version if none exists yet, otherwise adds a
        new active version (deactivating the previous one) — same
        create-vs-add-version branch every other "make sure this exact
        content is what's served" caller in this codebase already uses
        (see backend/ai/prompts.py's ensure_prompt()). Always status="active":
        PromptRegistry's own default ("draft") would leave this
        unservable, and a global system prompt with no way to be inactive
        by policy is the entire point of this class."""
        if self.registry.get_active_version(self.NAME) is None:
            self.registry.create_prompt(
                self.NAME, "Global system prompt", content, status="active")
        else:
            self.registry.add_version(self.NAME, content, is_active=True, status="active")

    def list_prompts(self) -> List[str]:
        """Every historical version's template text, oldest first — the
        full history of the one system prompt, not PromptRegistry.list_prompts()'s
        "every name's current state" (different question, same-looking name)."""
        rows = (
            self.registry.db.query(PromptVersion)
            .filter_by(name=self.NAME)
            .order_by(PromptVersion.version)
            .all()
        )
        return [r.template for r in rows]
