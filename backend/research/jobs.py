"""W6 — Long-running research jobs (literature review, theme map).

Results are stored on an OutboxEvent with ``event_type=research_job.result``
(status=dispatched so the outbox poller ignores them). Poll via
GET /api/research/jobs/<job_id>.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from backend.evidence.objects import serialize_evidence_object
from backend.evidence.themes import discover_themes, themes_to_markdown
from backend.evidence.writing.citation_binder import BINDER_VERSION
from backend.evidence.writing.reviewer_persistence import persist_reviewer_run
from backend.evidence.conflict import apply_conflict_stage
from backend.evidence.consensus import apply_consensus_stage
from backend.evidence.ranking import apply_ranking_stage
from backend.evidence.reasoning import apply_reasoning_stage
from backend.evidence.retrieval import retrieve_evidence_objects
from backend.evidence.writing_intelligence import apply_writing_intelligence_stage

RESULT_EVENT = "research_job.result"


def store_research_job_result(
    db,
    *,
    OutboxEvent: Any,
    job_id: int,
    kind: str,
    result: dict[str, Any],
) -> None:
    payload = {
        "kind": kind,
        "result": result,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    db.add(
        OutboxEvent(
            aggregate_type="upload_job",
            aggregate_id=int(job_id),
            event_type=RESULT_EVENT,
            payload=json.dumps(payload, ensure_ascii=False, default=str),
            status="dispatched",
        )
    )
    db.commit()


def load_research_job_result(
    db,
    *,
    OutboxEvent: Any,
    select: Any,
    job_id: int,
) -> Optional[dict[str, Any]]:
    rows = (
        db.execute(
            select(OutboxEvent)
            .where(
                OutboxEvent.aggregate_type == "upload_job",
                OutboxEvent.aggregate_id == int(job_id),
                OutboxEvent.event_type == RESULT_EVENT,
            )
            .order_by(OutboxEvent.id.desc())
        )
        .scalars()
        .all()
    )
    for ev in rows:
        try:
            data = json.loads(ev.payload or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("result"), dict):
            return data
    return None


def run_theme_map_job(
    db,
    *,
    user_id: int,
    project_id: int,
    EvidenceObject: Any,
    select: Any,
    file_ids: list[int] | None = None,
    status_filter: list[str] | None = None,
) -> dict[str, Any]:
    """Deterministic theme map over project evidence (async-capable)."""
    statuses = status_filter or ["candidate", "accepted"]
    filters = [
        EvidenceObject.user_id == user_id,
        EvidenceObject.project_id == project_id,
        EvidenceObject.status.in_(statuses),
        EvidenceObject.status != "superseded",
    ]
    if file_ids:
        filters.append(EvidenceObject.file_id.in_([int(x) for x in file_ids]))
    rows = list(db.execute(select(EvidenceObject).where(*filters)).scalars().all())
    objects = [serialize_evidence_object(r) for r in rows]
    payload = discover_themes(objects, project_id=project_id)
    return {
        "kind": "theme_map",
        "project_id": project_id,
        "themes": payload,
        "markdown": themes_to_markdown(payload),
        "object_count": len(objects),
    }


def run_literature_review_job(
    db,
    *,
    user_id: int,
    query: dict[str, Any],
    EvidenceObject: Any,
    WritingSentenceBinding: Any,
    WritingDocument: Any,
    ReviewerRun: Any,
    ReviewerFinding: Any,
    select: Any,
    require_owned_document: Callable,
    enrich_bibliography: Callable | None = None,
    binding_relation_map: Callable | None = None,
    composer: Any = None,
    writing_quality_mode: str = "grounded_v1",
) -> dict[str, Any]:
    """Run grounded writing intelligence (same pipeline as sync POST)."""
    filters = dict(query.get("filters") or {})
    filters["status"] = ["accepted"]
    query = {**query, "filters": filters, "section_type": query.get("section_type") or "literature_review"}

    retrieved = retrieve_evidence_objects(
        db,
        query=query,
        EvidenceObject=EvidenceObject,
        WritingSentenceBinding=WritingSentenceBinding,
        select=select,
    )
    ranked = apply_ranking_stage(retrieved, ranking_strategy=query.get("ranking_strategy") or "default_v0")
    relations = {}
    if binding_relation_map is not None:
        relations = binding_relation_map(
            db,
            user_id=user_id,
            project_id=int(query["scope"]["project_id"]),
            document_id=int(query["scope"]["document_id"]) if query.get("scope", {}).get("document_id") else None,
        )
    consensus = apply_consensus_stage(ranked, binding_relations=relations)
    conflicted = apply_conflict_stage(consensus, binding_relations=relations)
    reasoned = apply_reasoning_stage(conflicted)
    result = apply_writing_intelligence_stage(reasoned, composer=composer)
    writing = result.get("writing") or {}
    if enrich_bibliography is not None:
        writing = enrich_bibliography(db, uid=user_id, writing=writing)
        result["writing"] = writing

    doc_id = (query.get("scope") or {}).get("document_id")
    review = writing.get("review")
    if doc_id is not None and isinstance(review, dict):
        doc = require_owned_document(
            db, WritingDocument, user_id=user_id, document_id=int(doc_id)
        )
        persist_reviewer_run(
            db,
            ReviewerRun=ReviewerRun,
            ReviewerFinding=ReviewerFinding,
            user_id=user_id,
            project_id=int(query["scope"]["project_id"]),
            document_id=int(doc_id),
            document_version_no=int(getattr(doc, "current_version", None) or 1),
            writing_version=str(writing.get("writing_version") or ""),
            review=review,
            sections=list(writing.get("sections") or []),
            consensus=result.get("consensus"),
            conflict=result.get("conflict"),
            supporting_count=writing.get("supporting_count"),
            binder_version=BINDER_VERSION,
            prompt_meta={
                "reviewer_kind": "rule_based",
                "writing_quality_mode": writing_quality_mode,
                "async_job": True,
            },
        )
        db.commit()

    return {
        "kind": "literature_review",
        "writing_version": result.get("writing_version"),
        "writing": writing,
        "consensus": result.get("consensus"),
        "conflict": result.get("conflict"),
        "metrics": result.get("metrics"),
    }
