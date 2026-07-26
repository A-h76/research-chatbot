"""Workspace navigation references — aligned with SPA ``WorkspaceReference``.

Sprint 1: schema only. Not yet emitted by live chat/writing routes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

WorkspaceTab = Literal[
    "overview",
    "structure",
    "classification",
    "entities",
    "evidence",
    "graph",
    "narrative",
    "chat",
]

WorkspaceReferenceKind = Literal[
    "structure.section",
    "classification.decision",
    "entity",
    "evidence.framework",
    "evidence.outcome",
    "graph.node",
    "graph.edge",
]


@dataclass(frozen=True)
class WorkspaceReference:
    """Semantic link into the Paper Workspace — not a raw hyperlink."""

    id: str
    kind: WorkspaceReferenceKind
    ref_id: str
    tab: WorkspaceTab
    label: str | None = None
    href: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
