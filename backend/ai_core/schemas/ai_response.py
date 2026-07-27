"""Canonical AI feature response contract (Phase B target; schema in Sprint 1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from backend.ai_core.schemas.workspace_reference import WorkspaceReference

ConfidenceLevel = Literal["High", "Medium", "Low"]


@dataclass
class EvidenceReference:
    """Lightweight evidence pointer attached to an answer.

    May later wrap or replace ad-hoc citation dicts. Distinct from
    ``WorkspaceReference`` (navigation) though both can appear together.
    """

    id: str
    label: str
    source: str | None = None
    excerpt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIResponse:
    """Shared shape for chat, writing, compare, critique, etc.

    Sprint 1: schema only — validators and routers do not emit this yet.
    """

    answer: str
    confidence: ConfidenceLevel
    evidence: list[EvidenceReference] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    workspace_refs: list[WorkspaceReference] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
