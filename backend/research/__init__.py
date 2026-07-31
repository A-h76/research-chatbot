"""Research Engine — shared retrieve / cite / scope for chat + writing.

W1–W2 of the Dhund research loop. W7 Research Session will attach to the
same scope + reference payloads (session_id is forward-compatible).
"""

from .citations import passages_to_workspace_references
from .message_payload import (
    dump_message_sources,
    load_message_sources,
    normalize_sources_for_api,
)
from .retrieve import PassageHit, research_retrieve
from .scope import ResearchScope
from .skills import get_skill, normalize_skill_id, skill_catalog
from .structured_extract import (
    build_structured_extract_table,
    table_prompt_block,
    table_to_csv,
    table_to_markdown,
)
from .verify import GroundingReport, verify_chat_grounding

__all__ = [
    "GroundingReport",
    "PassageHit",
    "ResearchScope",
    "build_structured_extract_table",
    "dump_message_sources",
    "get_skill",
    "load_message_sources",
    "normalize_skill_id",
    "normalize_sources_for_api",
    "passages_to_workspace_references",
    "research_retrieve",
    "skill_catalog",
    "table_prompt_block",
    "table_to_csv",
    "table_to_markdown",
    "verify_chat_grounding",
]
