"""Research scope — explicit, not inferred from the page (W2 / session-ready)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Optional

ScopeMode = Literal["paper", "conversation", "project", "collection", "library"]


@dataclass(frozen=True)
class ResearchScope:
    """What a research turn is allowed to read.

    ``session_id`` is reserved for W7 Research Session Engine — nullable until then.
    """

    user_id: int
    mode: ScopeMode = "conversation"
    file_id: Optional[int] = None
    conversation_id: Optional[int] = None
    project_id: Optional[int] = None
    collection_id: Optional[int] = None
    session_id: Optional[str] = None
    web: Literal["off", "auto", "on"] = "off"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def for_chat(
        cls,
        *,
        user_id: int,
        conversation_id: int,
        project_id: Optional[int],
        file_id: Optional[int],
        search_mode: str = "off",
        session_id: Optional[str] = None,
        collection_id: Optional[int] = None,
    ) -> "ResearchScope":
        web: Literal["off", "auto", "on"]
        if search_mode in ("on", "auto", "off"):
            web = search_mode  # type: ignore[assignment]
        else:
            web = "off"
        if file_id is not None:
            mode: ScopeMode = "paper"
        elif collection_id is not None:
            mode = "collection"
        elif project_id is not None:
            mode = "project"
        else:
            mode = "conversation"
        return cls(
            user_id=user_id,
            mode=mode,
            file_id=file_id,
            conversation_id=conversation_id,
            project_id=project_id,
            collection_id=collection_id,
            session_id=session_id,
            web=web if file_id is None else "off",
        )
