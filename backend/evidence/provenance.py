"""Provenance and content-hash helpers for EvidenceObject identity."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return str(value).strip()


def compute_content_hash(
    *,
    file_id: int,
    page: int | None,
    char_start: int | None,
    char_end: int | None,
    quote: str,
    claim: str,
) -> str:
    payload = "|".join(
        [
            _canonical(file_id),
            _canonical(page),
            _canonical(char_start),
            _canonical(char_end),
            _canonical(quote).lower(),
            _canonical(claim).lower(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_input_content_hash(
    *,
    file_fingerprint: str,
    document_understanding_version: str = "",
    evidence_grading_version: str = "",
    knowledge_graph_version: str = "",
    extraction_prompt_version: str = "",
    pipeline_version: str,
) -> str:
    payload = "|".join(
        [
            _canonical(file_fingerprint),
            _canonical(document_understanding_version),
            _canonical(evidence_grading_version),
            _canonical(knowledge_graph_version),
            _canonical(extraction_prompt_version),
            _canonical(pipeline_version),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_provenance(
    *,
    pipeline_version: str,
    document_understanding: str | dict[str, Any] | None = None,
    evidence_grading: str | dict[str, Any] | None = None,
    knowledge_graph: str | dict[str, Any] | None = None,
    extraction_prompt_version: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provenance: dict[str, Any] = {
        "pipeline_version": pipeline_version,
        "document_understanding": document_understanding or "",
        "evidence_grading": evidence_grading or "",
        "knowledge_graph": knowledge_graph or "",
        "extraction_prompt_version": extraction_prompt_version or "",
    }
    if extra:
        provenance.update(extra)
    return provenance


def provenance_to_json(provenance: dict[str, Any]) -> str:
    return json.dumps(provenance, sort_keys=True, ensure_ascii=False)
