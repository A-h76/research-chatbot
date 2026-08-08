"""Assistant Engine — Dhund's decision brain (ADR-0018).

Decides *what* help the researcher needs. Capability Router decides *how*.
Never import server.
"""

from backend.assistant.engine import AssistantEngine, create_assistant_engine
from backend.assistant.research_state import (
    ResearchState,
    derive_journey,
    research_state_to_dict,
)
from backend.assistant.prompt_layers import compose_assistant_layers

__all__ = [
    "AssistantEngine",
    "ResearchState",
    "compose_assistant_layers",
    "create_assistant_engine",
    "derive_journey",
    "research_state_to_dict",
]
