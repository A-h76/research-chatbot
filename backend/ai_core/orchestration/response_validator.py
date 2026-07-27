"""Validate model outputs against Dhund policies and ``AIResponse`` shape.

Stage 1 (Paper Chat) policy: Observe → Record → Warn only.
Never modify streamed/user-visible text. Never regenerate.
Regenerate / rewrite belongs in Stage 2+.

Sprint 3+: structural + policy checks. Callers may surface warnings;
they must not rewrite answers based on this validator in Stage 1.
"""

from __future__ import annotations

from typing import Any, get_args

from backend.ai_core.schemas.ai_response import AIResponse, ConfidenceLevel, EvidenceReference
from backend.ai_core.schemas.validation import ValidationResult
from backend.ai_core.schemas.workspace_reference import (
    WorkspaceReference,
    WorkspaceReferenceKind,
    WorkspaceTab,
)

_CONFIDENCE = set(get_args(ConfidenceLevel))
_KINDS = set(get_args(WorkspaceReferenceKind))
_TABS = set(get_args(WorkspaceTab))


class ResponseValidator:
    """Check answer, confidence, evidence, workspace refs, limitations."""

    def __init__(self, *, require_limitations_when_low: bool = True) -> None:
        self._require_limitations_when_low = require_limitations_when_low

    def validate(self, payload: AIResponse | dict[str, Any]) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        try:
            response = payload if isinstance(payload, AIResponse) else self._from_dict(payload)
        except (TypeError, ValueError, KeyError) as exc:
            return ValidationResult(ok=False, errors=[f"invalid_payload: {exc}"])

        if not (response.answer or "").strip():
            errors.append("answer_empty")

        if response.confidence not in _CONFIDENCE:
            errors.append(f"confidence_invalid:{response.confidence!r}")

        for i, ref in enumerate(response.workspace_refs):
            if ref.kind not in _KINDS:
                errors.append(f"workspace_ref[{i}].kind_invalid:{ref.kind!r}")
            if ref.tab not in _TABS:
                errors.append(f"workspace_ref[{i}].tab_invalid:{ref.tab!r}")
            if not (ref.ref_id or "").strip():
                errors.append(f"workspace_ref[{i}].ref_id_empty")
            if not (ref.id or "").strip():
                errors.append(f"workspace_ref[{i}].id_empty")

        for i, ev in enumerate(response.evidence):
            if not (ev.id or "").strip():
                errors.append(f"evidence[{i}].id_empty")
            if not (ev.label or "").strip():
                errors.append(f"evidence[{i}].label_empty")

        if response.confidence == "High" and not response.evidence and not response.workspace_refs:
            warnings.append("high_confidence_without_evidence")

        if (
            self._require_limitations_when_low
            and response.confidence == "Low"
            and not response.limitations
        ):
            warnings.append("low_confidence_without_limitations")

        ok = not errors
        return ValidationResult(
            ok=ok,
            response=response if ok else None,
            errors=errors,
            warnings=warnings,
        )

    def _from_dict(self, data: dict[str, Any]) -> AIResponse:
        evidence_raw = data.get("evidence") or []
        refs_raw = data.get("workspace_refs") or data.get("workspace_references") or []
        evidence = [
            e if isinstance(e, EvidenceReference) else EvidenceReference(**e)
            for e in evidence_raw
        ]
        refs = [
            r if isinstance(r, WorkspaceReference) else WorkspaceReference(**r)
            for r in refs_raw
        ]
        return AIResponse(
            answer=str(data.get("answer", "")),
            confidence=data["confidence"],  # type: ignore[arg-type]
            evidence=evidence,
            limitations=list(data.get("limitations") or []),
            workspace_refs=refs,
            metadata=dict(data.get("metadata") or {}),
        )
