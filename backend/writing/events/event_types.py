from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class WritingEvent:
    name: str
    user_id: int
    document_id: int
    metadata: dict
    created_at: str


def make_writing_event(name: str, *, user_id: int, document_id: int, metadata: dict | None = None) -> WritingEvent:
    return WritingEvent(
        name=name,
        user_id=int(user_id),
        document_id=int(document_id),
        metadata=metadata or {},
        created_at=datetime.now(timezone.utc).isoformat(),
    )

