"""Flask blueprint factory for Evidence Layer routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from flask import Blueprint, jsonify, request, session

from backend.evidence.api.errors import ErrorCode, EvidenceDomainError
from backend.evidence.bindings import validate_binding_payload
from backend.evidence.inspector import assemble_explain_response
from backend.evidence.objects import serialize_evidence_object
from backend.evidence.consensus import apply_consensus_stage
from backend.evidence.query import normalize_evidence_query
from backend.evidence.ranking import apply_ranking_stage
from backend.evidence.retrieval import retrieve_evidence_objects
from backend.evidence.reviews import next_object_status_after_review, validate_review_payload
from backend.evidence.services.extract_service import PIPELINE_VERSION, run_evidence_extraction
from backend.evidence.services.logging import log_evidence_metric
from backend.evidence.services.permission_service import (
    require_owned_document,
    require_owned_evidence,
    require_owned_file,
    require_owned_project,
)


def create_evidence_blueprint(
    *,
    SessionLocal: Any,
    Project: Any,
    UserFile: Any,
    WritingDocument: Any,
    EvidenceObject: Any,
    ClaimReview: Any,
    WritingSentenceBinding: Any,
    EvidenceExtractionRun: Any,
    AnalysisPipelineResult: Any,
    UploadJob: Any,
    OutboxEvent: Any,
    select: Any,
    login_required: Callable,
    limiter: Any,
    load_analysis_result: Callable,
    enqueue_job: Callable | None = None,
) -> Blueprint:
    bp = Blueprint("evidence", __name__)

    def _uid() -> int:
        return int(session["user_id"])

    def _err(exc: EvidenceDomainError, status: int = 404):
        code_map = {
            ErrorCode.VALIDATION: 422,
            ErrorCode.AUTHZ_DENIED: 403,
            ErrorCode.NOT_FOUND: 404,
            ErrorCode.NOT_READY: 422,
            ErrorCode.RATE_LIMITED: 429,
        }
        return jsonify({"error": exc.code, "detail": exc.detail}), code_map.get(exc.code, status)

    @bp.get("/api/projects/<int:project_id>/evidence")
    @login_required
    def list_evidence(project_id: int):
        uid = _uid()
        db = SessionLocal()
        try:
            require_owned_project(db, Project, user_id=uid, project_id=project_id)
            stmt = select(EvidenceObject).where(
                EvidenceObject.user_id == uid,
                EvidenceObject.project_id == project_id,
                EvidenceObject.status != "superseded",
            )
            file_id = request.args.get("file_id")
            status = request.args.get("status")
            if file_id:
                stmt = stmt.where(EvidenceObject.file_id == int(file_id))
            if status:
                stmt = stmt.where(EvidenceObject.status == status)
            rows = db.execute(stmt.order_by(EvidenceObject.updated_at.desc()).limit(200)).scalars().all()
            return jsonify({"items": [serialize_evidence_object(r) for r in rows], "count": len(rows)})
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.get("/api/evidence/<int:evidence_id>")
    @login_required
    def get_evidence(evidence_id: int):
        uid = _uid()
        db = SessionLocal()
        try:
            row = require_owned_evidence(db, EvidenceObject, user_id=uid, evidence_id=evidence_id)
            return jsonify(serialize_evidence_object(row))
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.post("/api/evidence/<int:evidence_id>/reviews")
    @login_required
    @limiter.limit("60 per hour")
    def review_evidence(evidence_id: int):
        uid = _uid()
        data = request.get_json(silent=True) or {}
        db = SessionLocal()
        try:
            row = require_owned_evidence(db, EvidenceObject, user_id=uid, evidence_id=evidence_id)
            payload = validate_review_payload(data)
            review = ClaimReview(
                evidence_object_id=row.id,
                user_id=uid,
                project_id=row.project_id,
                status=payload["status"],
                reason=payload["reason"],
                edited_claim=payload.get("edited_claim"),
                edited_quote=payload.get("edited_quote"),
                reviewed_at=datetime.now(timezone.utc),
            )
            db.add(review)
            if payload["status"] == "edited":
                # Append-only: supersede with edited content
                new_row = EvidenceObject(
                    user_id=row.user_id,
                    project_id=row.project_id,
                    file_id=row.file_id,
                    page=row.page,
                    char_start=row.char_start,
                    char_end=row.char_end,
                    section=row.section,
                    quote=payload.get("edited_quote") or row.quote,
                    claim=payload.get("edited_claim") or row.claim,
                    study_type=row.study_type,
                    study_quality=row.study_quality,
                    supports_json=row.supports_json,
                    contradicts_json=row.contradicts_json,
                    limitations_json=row.limitations_json,
                    confidence_band=row.confidence_band,
                    status="accepted",
                    pipeline_version=row.pipeline_version,
                    created_by="user",
                    content_hash=row.content_hash + ":edited",
                    supersedes_id=row.id,
                    provenance_json=row.provenance_json,
                    source_kg_node_id=row.source_kg_node_id,
                )
                row.status = "superseded"
                db.add(new_row)
            else:
                row.status = next_object_status_after_review(payload["status"])
            row.updated_at = datetime.now(timezone.utc)
            db.commit()
            log_evidence_metric("review", user_id=uid, evidence_id=evidence_id, status=payload["status"])
            return jsonify({"ok": True, "evidence": serialize_evidence_object(row if payload["status"] != "edited" else new_row)})
        except ValueError as exc:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": str(exc)}), 422
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.post("/api/documents/<int:document_id>/evidence-bindings")
    @login_required
    @limiter.limit("120 per hour")
    def create_binding(document_id: int):
        uid = _uid()
        data = request.get_json(silent=True) or {}
        db = SessionLocal()
        try:
            doc = require_owned_document(db, WritingDocument, user_id=uid, document_id=document_id)
            payload = validate_binding_payload(data)
            ev = require_owned_evidence(
                db, EvidenceObject, user_id=uid, evidence_id=payload["evidence_object_id"]
            )
            if int(ev.project_id) != int(doc.project_id):
                raise EvidenceDomainError(ErrorCode.NOT_FOUND, "evidence_not_in_project")
            binding = WritingSentenceBinding(
                user_id=uid,
                project_id=doc.project_id,
                document_id=doc.id,
                evidence_object_id=ev.id,
                block_id=payload["block_id"],
                range_start=payload["range_start"],
                range_end=payload["range_end"],
                selected_text=payload["selected_text"],
                relation=payload["relation"],
                created_by="user",
            )
            db.add(binding)
            db.commit()
            return jsonify({"id": binding.id, "document_id": doc.id, **payload}), 201
        except ValueError as exc:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": str(exc)}), 422
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.get("/api/documents/<int:document_id>/evidence-bindings")
    @login_required
    def list_bindings(document_id: int):
        uid = _uid()
        db = SessionLocal()
        try:
            require_owned_document(db, WritingDocument, user_id=uid, document_id=document_id)
            rows = (
                db.execute(
                    select(WritingSentenceBinding)
                    .where(
                        WritingSentenceBinding.user_id == uid,
                        WritingSentenceBinding.document_id == document_id,
                    )
                    .order_by(WritingSentenceBinding.created_at.desc())
                )
                .scalars()
                .all()
            )
            items = [
                {
                    "id": b.id,
                    "document_id": b.document_id,
                    "evidence_object_id": b.evidence_object_id,
                    "block_id": b.block_id,
                    "range_start": b.range_start,
                    "range_end": b.range_end,
                    "selected_text": b.selected_text,
                    "relation": b.relation,
                }
                for b in rows
            ]
            return jsonify({"items": items, "count": len(items)})
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.delete("/api/evidence-bindings/<int:binding_id>")
    @login_required
    def delete_binding(binding_id: int):
        uid = _uid()
        db = SessionLocal()
        try:
            row = db.get(WritingSentenceBinding, binding_id)
            if not row or int(row.user_id) != uid:
                raise EvidenceDomainError(ErrorCode.NOT_FOUND, "binding_not_found")
            db.delete(row)
            db.commit()
            return jsonify({"ok": True})
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.post("/api/projects/<int:project_id>/evidence/extract")
    @login_required
    @limiter.limit("30 per hour")
    def enqueue_extract(project_id: int):
        uid = _uid()
        data = request.get_json(silent=True) or {}
        file_id = data.get("file_id")
        force = bool(data.get("force"))
        if not file_id:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": "file_id required"}), 422
        db = SessionLocal()
        try:
            require_owned_project(db, Project, user_id=uid, project_id=project_id)
            require_owned_file(db, UserFile, user_id=uid, file_id=int(file_id), project_id=project_id)
            # Synchronous extract for MVP reliability in tests; also enqueue for worker chain
            result = run_evidence_extraction(
                db,
                user_id=uid,
                project_id=project_id,
                file_id=int(file_id),
                UserFile=UserFile,
                AnalysisPipelineResult=AnalysisPipelineResult,
                EvidenceObject=EvidenceObject,
                EvidenceExtractionRun=EvidenceExtractionRun,
                load_analysis_result=load_analysis_result,
                force=force,
                pipeline_version=PIPELINE_VERSION,
            )
            job_id = None
            if enqueue_job is not None:
                job = UploadJob(
                    file_id=int(file_id),
                    user_id=uid,
                    job_type="evidence_extract",
                    status="pending",
                )
                db.add(job)
                db.flush()
                db.add(
                    OutboxEvent(
                        aggregate_type="upload_job",
                        aggregate_id=job.id,
                        event_type="job.enqueued",
                        payload=json.dumps(
                            {
                                "file_id": int(file_id),
                                "project_id": project_id,
                                "force": force,
                                "pipeline_version": PIPELINE_VERSION,
                                # Mark already applied so worker can no-op unless force
                                "already_applied": True,
                                "run_id": result.get("run_id"),
                            }
                        ),
                    )
                )
                db.commit()
                job_id = job.id
            return jsonify({**result, "job_id": job_id, "pipeline_version": PIPELINE_VERSION})
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.post("/api/evidence/explain")
    @login_required
    @limiter.limit("120 per hour")
    def explain():
        uid = _uid()
        data = request.get_json(silent=True) or {}
        document_id = data.get("document_id")
        project_id = data.get("project_id")
        block_id = (data.get("block_id") or "").strip()
        range_start = data.get("range_start")
        range_end = data.get("range_end")
        selected_text = data.get("selected_text") or ""
        if not document_id or not project_id:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": "document_id and project_id required"}), 422
        if not block_id and (range_start is None or range_end is None):
            return jsonify({"error": ErrorCode.VALIDATION, "detail": "block_id or range required"}), 422

        db = SessionLocal()
        try:
            require_owned_project(db, Project, user_id=uid, project_id=int(project_id))
            doc = require_owned_document(db, WritingDocument, user_id=uid, document_id=int(document_id))
            if int(doc.project_id) != int(project_id):
                raise EvidenceDomainError(ErrorCode.NOT_FOUND, "document_not_in_project")

            stmt = select(WritingSentenceBinding).where(
                WritingSentenceBinding.user_id == uid,
                WritingSentenceBinding.document_id == doc.id,
            )
            bindings = []
            if block_id:
                bindings = (
                    db.execute(stmt.where(WritingSentenceBinding.block_id == block_id)).scalars().all()
                )
            if not bindings and range_start is not None and range_end is not None:
                bindings = (
                    db.execute(
                        stmt.where(
                            WritingSentenceBinding.range_start == int(range_start),
                            WritingSentenceBinding.range_end == int(range_end),
                        )
                    )
                    .scalars()
                    .all()
                )
            # Sticky selection fallback: exact selected_text match on existing bindings
            if not bindings and selected_text.strip():
                needle = selected_text.strip()
                all_bindings = db.execute(stmt).scalars().all()
                bindings = [b for b in all_bindings if (b.selected_text or "").strip() == needle]

            bound_objects = []
            relations = []
            file_ids = set()
            for b in bindings:
                ev = db.get(EvidenceObject, b.evidence_object_id)
                if not ev or int(ev.user_id) != uid:
                    continue
                if ev.status in {"rejected", "superseded"}:
                    continue
                bound_objects.append(ev)
                relations.append(b.relation or "supports")
                file_ids.add(ev.file_id)

            titles: dict[int, str] = {}
            if file_ids:
                files = db.execute(select(UserFile).where(UserFile.id.in_(list(file_ids)))).scalars().all()
                for f in files:
                    titles[f.id] = f.title or f.name or f"File {f.id}"

            sentence = {
                "block_id": block_id,
                "range_start": range_start,
                "range_end": range_end,
                "text": selected_text[:2000],
            }
            payload = assemble_explain_response(
                sentence=sentence,
                bound_objects=bound_objects,
                relations=relations,
                file_titles=titles,
            )
            log_evidence_metric(
                "explain",
                user_id=uid,
                document_id=doc.id,
                sufficiency=payload.get("sufficiency"),
                evidence_count=len(payload.get("evidence") or []),
            )
            return jsonify(payload)
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    def _run_retrieval():
        uid = _uid()
        data = request.get_json(silent=True) or {}
        # Allow either bare EvidenceQuery or { "query": { ... } }
        raw = data.get("query") if isinstance(data.get("query"), dict) else data
        db = SessionLocal()
        try:
            query = normalize_evidence_query(raw, user_id=uid)
            require_owned_project(db, Project, user_id=uid, project_id=query["scope"]["project_id"])
            doc_id = query["scope"].get("document_id")
            if doc_id is not None:
                doc = require_owned_document(db, WritingDocument, user_id=uid, document_id=int(doc_id))
                if int(doc.project_id) != int(query["scope"]["project_id"]):
                    raise EvidenceDomainError(ErrorCode.NOT_FOUND, "document_not_in_project")
            result = retrieve_evidence_objects(
                db,
                query=query,
                EvidenceObject=EvidenceObject,
                WritingSentenceBinding=WritingSentenceBinding,
                select=select,
            )
            log_evidence_metric(
                "retrieval",
                user_id=uid,
                project_id=query["scope"]["project_id"],
                intent=query["intent"],
                total=result.get("total"),
                returned=len(result.get("objects") or []),
            )
            return jsonify(result)
        except ValueError as exc:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": str(exc)}), 422
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.post("/api/evidence/search")
    @login_required
    @limiter.limit("120 per hour")
    def evidence_search():
        """Retrieval stage: EvidenceQuery → EvidenceObject[]."""
        return _run_retrieval()

    @bp.post("/api/evidence/retrieve")
    @login_required
    @limiter.limit("120 per hour")
    def evidence_retrieve():
        """Alias of /search — same EvidenceQuery contract (Sprint 1)."""
        return _run_retrieval()

    def _run_ranking():
        """Ranking stage: EvidenceQuery → Retrieval → reorder EvidenceObjects."""
        uid = _uid()
        data = request.get_json(silent=True) or {}
        raw = data.get("query") if isinstance(data.get("query"), dict) else data
        db = SessionLocal()
        try:
            query = normalize_evidence_query(raw, user_id=uid)
            require_owned_project(db, Project, user_id=uid, project_id=query["scope"]["project_id"])
            doc_id = query["scope"].get("document_id")
            if doc_id is not None:
                doc = require_owned_document(db, WritingDocument, user_id=uid, document_id=int(doc_id))
                if int(doc.project_id) != int(query["scope"]["project_id"]):
                    raise EvidenceDomainError(ErrorCode.NOT_FOUND, "document_not_in_project")
            retrieved = retrieve_evidence_objects(
                db,
                query=query,
                EvidenceObject=EvidenceObject,
                WritingSentenceBinding=WritingSentenceBinding,
                select=select,
            )
            result = apply_ranking_stage(retrieved, ranking_strategy=query["ranking_strategy"])
            log_evidence_metric(
                "ranking",
                user_id=uid,
                project_id=query["scope"]["project_id"],
                intent=query["intent"],
                strategy=query["ranking_strategy"],
                total=result.get("total"),
                returned=len(result.get("objects") or []),
            )
            return jsonify(result)
        except ValueError as exc:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": str(exc)}), 422
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.post("/api/evidence/rank")
    @login_required
    @limiter.limit("120 per hour")
    def evidence_rank():
        """Ranking stage: EvidenceQuery → Retrieval → ranked EvidenceObject[]."""
        return _run_ranking()

    def _binding_relation_map(db, *, user_id: int, project_id: int, document_id: int | None) -> dict[int, str]:
        if document_id is None or WritingSentenceBinding is None:
            return {}
        rows = db.execute(
            select(WritingSentenceBinding).where(
                WritingSentenceBinding.user_id == user_id,
                WritingSentenceBinding.project_id == project_id,
                WritingSentenceBinding.document_id == int(document_id),
            )
        ).scalars().all()
        out: dict[int, str] = {}
        for b in rows:
            out[int(b.evidence_object_id)] = (b.relation or "supports").strip().lower()
        return out

    def _run_consensus():
        """Consensus stage: EvidenceQuery → Retrieval → Ranking → aggregate."""
        uid = _uid()
        data = request.get_json(silent=True) or {}
        raw = data.get("query") if isinstance(data.get("query"), dict) else data
        db = SessionLocal()
        try:
            query = normalize_evidence_query(raw, user_id=uid)
            require_owned_project(db, Project, user_id=uid, project_id=query["scope"]["project_id"])
            doc_id = query["scope"].get("document_id")
            if doc_id is not None:
                doc = require_owned_document(db, WritingDocument, user_id=uid, document_id=int(doc_id))
                if int(doc.project_id) != int(query["scope"]["project_id"]):
                    raise EvidenceDomainError(ErrorCode.NOT_FOUND, "document_not_in_project")
            retrieved = retrieve_evidence_objects(
                db,
                query=query,
                EvidenceObject=EvidenceObject,
                WritingSentenceBinding=WritingSentenceBinding,
                select=select,
            )
            ranked = apply_ranking_stage(retrieved, ranking_strategy=query["ranking_strategy"])
            relations = _binding_relation_map(
                db,
                user_id=uid,
                project_id=int(query["scope"]["project_id"]),
                document_id=int(doc_id) if doc_id is not None else None,
            )
            result = apply_consensus_stage(ranked, binding_relations=relations)
            log_evidence_metric(
                "consensus",
                user_id=uid,
                project_id=query["scope"]["project_id"],
                intent=query["intent"],
                label=(result.get("consensus") or {}).get("label"),
                supporting=(result.get("consensus") or {}).get("supporting"),
                contradicting=(result.get("consensus") or {}).get("contradicting"),
            )
            return jsonify(result)
        except ValueError as exc:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": str(exc)}), 422
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.post("/api/evidence/consensus")
    @login_required
    @limiter.limit("120 per hour")
    def evidence_consensus():
        """Consensus stage: EvidenceQuery → ranked EvidenceObjects + aggregate."""
        return _run_consensus()

    return bp
