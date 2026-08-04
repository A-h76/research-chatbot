"""Flask blueprint factory for Evidence Layer routes."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Callable

from flask import Blueprint, jsonify, request, session
from sqlalchemy import func

from backend.evidence.api.errors import ErrorCode, EvidenceDomainError
from backend.evidence.bindings import validate_binding_payload
from backend.evidence.envelope import stamp_ri_envelope
from backend.evidence.inspector import assemble_explain_response
from backend.evidence.matrix import (
        build_evidence_matrix,
        matrix_to_csv,
        matrix_to_markdown,
    )
from backend.evidence.themes import discover_themes, themes_to_markdown
from backend.evidence.graph import build_project_graph
from backend.evidence.gaps import discover_gaps, gaps_to_markdown
from backend.evidence.timeline import build_timeline, timeline_to_markdown
from backend.evidence.methodology import build_methodology_advice, methodology_to_markdown
from backend.evidence.consensus import aggregate_consensus
from backend.evidence.conflict import analyze_conflicts
from backend.evidence.objects import serialize_evidence_object
from backend.evidence.conflict import apply_conflict_stage
from backend.evidence.consensus import apply_consensus_stage
from backend.evidence.query import normalize_evidence_query
from backend.evidence.ranking import apply_ranking_stage
from backend.evidence.reasoning import apply_reasoning_stage
from backend.evidence.retrieval import retrieve_evidence_objects
from backend.evidence.writing_intelligence import apply_writing_intelligence_stage
from backend.evidence.writing.citation_binder import BINDER_VERSION
from backend.evidence.writing.reviewer_persistence import (
    persist_reviewer_run,
    serialize_run,
)
from backend.evidence.decisions import (
    DECISION_LABELS,
    REASON_PRESETS,
    decision_type_from_review_status,
    serialize_decision,
    validate_decision_payload,
)
from backend.evidence.reviews import next_object_status_after_review, validate_review_payload
from backend.evidence.services.extract_service import PIPELINE_VERSION, run_evidence_extraction
from backend.evidence.phase_projector import EXTRACTION_PROMPT_VERSION
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
    ResearchDecision: Any,
    WritingSentenceBinding: Any,
    EvidenceExtractionRun: Any,
    ReviewerRun: Any,
    ReviewerFinding: Any,
    AnalysisPipelineResult: Any,
    UploadJob: Any,
    OutboxEvent: Any,
    select: Any,
    login_required: Callable,
    limiter: Any,
    load_analysis_result: Callable,
    enqueue_job: Callable | None = None,
    ai_gateway: Any = None,
    get_model_registry: Callable | None = None,
    writing_quality_mode: str = "balanced",
    PaperAnalysis: Any = None,
    WorkflowEvent: Any = None,
    ai_gate: Any = None,
    feature_flag_service: Any = None,
    writing_intelligence_flag: str = "writing_intelligence",
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

    def _emit_contract_event(
        db,
        *,
        aggregate_type: str,
        aggregate_id: int,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Write contract-level event as already-dispatched outbox record."""
        db.add(
            OutboxEvent(
                aggregate_type=aggregate_type,
                aggregate_id=int(aggregate_id),
                event_type=event_type,
                payload=json.dumps(payload, ensure_ascii=False),
                status="dispatched",
                dispatched_at=datetime.now(timezone.utc),
            )
        )

    def _json_ri(result: dict[str, Any], *, started: float):
        """Stamp shared RI envelope fields (timing_ms, versions) then jsonify."""
        timing_ms = (time.perf_counter() - started) * 1000.0
        return jsonify(stamp_ri_envelope(result, timing_ms=timing_ms))

    @bp.get("/api/projects/<int:project_id>/evidence")
    @login_required
    def list_evidence(project_id: int):
        uid = _uid()
        db = SessionLocal()
        try:
            require_owned_project(db, Project, user_id=uid, project_id=project_id)
            filters = [
                EvidenceObject.user_id == uid,
                EvidenceObject.project_id == project_id,
                EvidenceObject.status != "superseded",
            ]
            file_id = request.args.get("file_id")
            status = request.args.get("status")
            try:
                limit = int(request.args.get("limit") or 50)
            except ValueError:
                return jsonify({"error": ErrorCode.VALIDATION, "detail": "limit must be an integer"}), 422
            try:
                offset = int(request.args.get("offset") or 0)
            except ValueError:
                return jsonify({"error": ErrorCode.VALIDATION, "detail": "offset must be an integer"}), 422
            limit = max(1, min(200, limit))
            offset = max(0, offset)
            if file_id:
                filters.append(EvidenceObject.file_id == int(file_id))
            if status:
                filters.append(EvidenceObject.status == status)
            rows = (
                db.execute(
                    select(EvidenceObject)
                    .where(*filters)
                    .order_by(EvidenceObject.updated_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                .scalars()
                .all()
            )
            total = int(
                db.execute(select(func.count()).select_from(EvidenceObject).where(*filters)).scalar_one()
            )
            return jsonify(
                {
                    "items": [serialize_evidence_object(r) for r in rows],
                    "count": len(rows),
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                }
            )
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.get("/api/projects/<int:project_id>/evidence/matrix")
    @login_required
    def evidence_matrix(project_id: int):
        """RI-002 — Evidence Matrix (Paper × Method × Dataset × Findings × Limitations)."""
        from flask import Response

        uid = _uid()
        fmt = (request.args.get("format") or "json").strip().lower()
        if fmt not in {"json", "markdown", "md", "csv"}:
            return (
                jsonify(
                    {
                        "error": ErrorCode.VALIDATION,
                        "detail": "format must be json, markdown, or csv",
                    }
                ),
                422,
            )
        if fmt == "md":
            fmt = "markdown"

        file_ids_raw = (request.args.get("file_ids") or "").strip()
        status_filter = (request.args.get("status") or "").strip()
        db = SessionLocal()
        try:
            require_owned_project(db, Project, user_id=uid, project_id=project_id)
            file_q = select(UserFile).where(
                UserFile.user_id == uid,
                UserFile.project_id == project_id,
            )
            if file_ids_raw:
                try:
                    wanted = [int(x) for x in file_ids_raw.split(",") if x.strip()]
                except ValueError:
                    return (
                        jsonify(
                            {
                                "error": ErrorCode.VALIDATION,
                                "detail": "file_ids must be comma-separated integers",
                            }
                        ),
                        422,
                    )
                if not wanted:
                    return (
                        jsonify(
                            {
                                "error": ErrorCode.VALIDATION,
                                "detail": "file_ids must include at least one id",
                            }
                        ),
                        422,
                    )
                file_q = file_q.where(UserFile.id.in_(wanted))
            files = list(db.execute(file_q.order_by(UserFile.id.asc())).scalars().all())

            ev_filters = [
                EvidenceObject.user_id == uid,
                EvidenceObject.project_id == project_id,
                EvidenceObject.status != "superseded",
            ]
            if status_filter:
                allowed = {s.strip() for s in status_filter.split(",") if s.strip()}
                if not allowed.issubset({"candidate", "accepted", "rejected"}):
                    return (
                        jsonify(
                            {
                                "error": ErrorCode.VALIDATION,
                                "detail": "status filter invalid",
                            }
                        ),
                        422,
                    )
                ev_filters.append(EvidenceObject.status.in_(sorted(allowed)))
            else:
                ev_filters.append(EvidenceObject.status.in_(["candidate", "accepted"]))

            if files:
                fids = [int(f.id) for f in files]
                ev_filters.append(EvidenceObject.file_id.in_(fids))
                evidence_rows = list(
                    db.execute(select(EvidenceObject).where(*ev_filters)).scalars().all()
                )
            else:
                evidence_rows = []

            evidence_by_file: dict[int, list] = {int(f.id): [] for f in files}
            for row in evidence_rows:
                fid = int(row.file_id)
                if fid in evidence_by_file:
                    evidence_by_file[fid].append(serialize_evidence_object(row))

            analysis_by_file: dict[int, dict] = {}
            if PaperAnalysis is not None and files:
                fids = [int(f.id) for f in files]
                pa_rows = list(
                    db.execute(
                        select(PaperAnalysis).where(PaperAnalysis.file_id.in_(fids))
                    )
                    .scalars()
                    .all()
                )
                for pa in pa_rows:
                    raw = getattr(pa, "data", None) or "{}"
                    try:
                        data = json.loads(raw) if isinstance(raw, str) else (raw or {})
                    except Exception:
                        data = {}
                    if isinstance(data, dict):
                        analysis_by_file[int(pa.file_id)] = data

            papers = [
                {
                    "id": int(f.id),
                    "file_id": int(f.id),
                    "title": getattr(f, "title", None) or getattr(f, "name", "") or "",
                    "name": getattr(f, "name", "") or "",
                    "year": getattr(f, "year", None) or "",
                    "authors": getattr(f, "authors", None) or "",
                }
                for f in files
            ]
            matrix = build_evidence_matrix(
                project_id=project_id,
                papers=papers,
                evidence_by_file=evidence_by_file,
                analysis_by_file=analysis_by_file,
            )

            if fmt == "markdown":
                body = matrix_to_markdown(matrix)
                return Response(
                    body,
                    mimetype="text/markdown; charset=utf-8",
                    headers={
                        "Content-Disposition": (
                            f'attachment; filename="evidence-matrix-p{project_id}.md"'
                        )
                    },
                )
            if fmt == "csv":
                body = matrix_to_csv(matrix)
                return Response(
                    body,
                    mimetype="text/csv; charset=utf-8",
                    headers={
                        "Content-Disposition": (
                            f'attachment; filename="evidence-matrix-p{project_id}.csv"'
                        )
                    },
                )
            return jsonify(matrix)
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.get("/api/projects/<int:project_id>/evidence/themes")
    @login_required
    def evidence_themes(project_id: int):
        """RI-001 — Theme Discovery (deterministic, reconstructable)."""
        from flask import Response

        uid = _uid()
        fmt = (request.args.get("format") or "json").strip().lower()
        if fmt not in {"json", "markdown", "md"}:
            return (
                jsonify(
                    {
                        "error": ErrorCode.VALIDATION,
                        "detail": "format must be json or markdown",
                    }
                ),
                422,
            )
        if fmt == "md":
            fmt = "markdown"

        def _float_arg(name: str, default: float) -> tuple[float | None, Any]:
            raw = request.args.get(name)
            if raw is None or raw == "":
                return default, None
            try:
                return float(raw), None
            except ValueError:
                return None, (
                    jsonify(
                        {
                            "error": ErrorCode.VALIDATION,
                            "detail": f"{name} must be a number",
                        }
                    ),
                    422,
                )

        def _int_arg(name: str, default: int) -> tuple[int | None, Any]:
            raw = request.args.get(name)
            if raw is None or raw == "":
                return default, None
            try:
                return int(raw), None
            except ValueError:
                return None, (
                    jsonify(
                        {
                            "error": ErrorCode.VALIDATION,
                            "detail": f"{name} must be an integer",
                        }
                    ),
                    422,
                )

        threshold, err = _float_arg("similarity_threshold", 0.22)
        if err:
            return err
        min_size, err = _int_arg("min_cluster_size", 2)
        if err:
            return err
        max_themes, err = _int_arg("max_themes", 12)
        if err:
            return err
        assert threshold is not None and min_size is not None and max_themes is not None
        if not (0.05 <= threshold <= 0.95):
            return (
                jsonify(
                    {
                        "error": ErrorCode.VALIDATION,
                        "detail": "similarity_threshold must be between 0.05 and 0.95",
                    }
                ),
                422,
            )
        if min_size < 1 or min_size > 20:
            return (
                jsonify(
                    {
                        "error": ErrorCode.VALIDATION,
                        "detail": "min_cluster_size must be 1–20",
                    }
                ),
                422,
            )
        if max_themes < 1 or max_themes > 40:
            return (
                jsonify(
                    {
                        "error": ErrorCode.VALIDATION,
                        "detail": "max_themes must be 1–40",
                    }
                ),
                422,
            )

        status_filter = (request.args.get("status") or "").strip()
        file_ids_raw = (request.args.get("file_ids") or "").strip()
        db = SessionLocal()
        try:
            require_owned_project(db, Project, user_id=uid, project_id=project_id)
            ev_filters = [
                EvidenceObject.user_id == uid,
                EvidenceObject.project_id == project_id,
                EvidenceObject.status != "superseded",
            ]
            if status_filter:
                allowed = {s.strip() for s in status_filter.split(",") if s.strip()}
                if not allowed.issubset({"candidate", "accepted", "rejected"}):
                    return (
                        jsonify(
                            {
                                "error": ErrorCode.VALIDATION,
                                "detail": "status filter invalid",
                            }
                        ),
                        422,
                    )
                ev_filters.append(EvidenceObject.status.in_(sorted(allowed)))
            else:
                ev_filters.append(EvidenceObject.status.in_(["candidate", "accepted"]))

            if file_ids_raw:
                try:
                    wanted = [int(x) for x in file_ids_raw.split(",") if x.strip()]
                except ValueError:
                    return (
                        jsonify(
                            {
                                "error": ErrorCode.VALIDATION,
                                "detail": "file_ids must be comma-separated integers",
                            }
                        ),
                        422,
                    )
                if wanted:
                    ev_filters.append(EvidenceObject.file_id.in_(wanted))

            rows = list(
                db.execute(
                    select(EvidenceObject)
                    .where(*ev_filters)
                    .order_by(EvidenceObject.id.asc())
                    .limit(2000)
                )
                .scalars()
                .all()
            )
            objects = [serialize_evidence_object(r) for r in rows]
            payload = discover_themes(
                objects,
                project_id=project_id,
                similarity_threshold=threshold,
                min_cluster_size=min_size,
                max_themes=max_themes,
            )
            if fmt == "markdown":
                body = themes_to_markdown(payload)
                return Response(
                    body,
                    mimetype="text/markdown; charset=utf-8",
                    headers={
                        "Content-Disposition": (
                            f'attachment; filename="evidence-themes-p{project_id}.md"'
                        )
                    },
                )
            return jsonify(payload)
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    def _load_project_corpus(db, *, uid: int, project_id: int, file_ids_raw: str, status_filter: str):
        """Shared loader for matrix/themes/graph/gaps project GETs."""
        require_owned_project(db, Project, user_id=uid, project_id=project_id)
        file_q = select(UserFile).where(
            UserFile.user_id == uid,
            UserFile.project_id == project_id,
        )
        wanted: list[int] | None = None
        if file_ids_raw:
            try:
                wanted = [int(x) for x in file_ids_raw.split(",") if x.strip()]
            except ValueError as exc:
                raise EvidenceDomainError(
                    ErrorCode.VALIDATION, "file_ids must be comma-separated integers"
                ) from exc
            if not wanted:
                raise EvidenceDomainError(ErrorCode.VALIDATION, "file_ids must include at least one id")
            file_q = file_q.where(UserFile.id.in_(wanted))
        files = list(db.execute(file_q.order_by(UserFile.id.asc())).scalars().all())

        ev_filters = [
            EvidenceObject.user_id == uid,
            EvidenceObject.project_id == project_id,
            EvidenceObject.status != "superseded",
        ]
        if status_filter:
            allowed = {s.strip() for s in status_filter.split(",") if s.strip()}
            if not allowed.issubset({"candidate", "accepted", "rejected"}):
                raise EvidenceDomainError(ErrorCode.VALIDATION, "status filter invalid")
            ev_filters.append(EvidenceObject.status.in_(sorted(allowed)))
        else:
            ev_filters.append(EvidenceObject.status.in_(["candidate", "accepted"]))
        if files:
            fids = [int(f.id) for f in files]
            ev_filters.append(EvidenceObject.file_id.in_(fids))
            evidence_rows = list(
                db.execute(
                    select(EvidenceObject).where(*ev_filters).order_by(EvidenceObject.id.asc()).limit(2000)
                )
                .scalars()
                .all()
            )
        else:
            evidence_rows = []

        objects = [serialize_evidence_object(r) for r in evidence_rows]
        papers = [
            {
                "id": int(f.id),
                "file_id": int(f.id),
                "title": getattr(f, "title", None) or getattr(f, "name", "") or "",
                "name": getattr(f, "name", "") or "",
                "year": getattr(f, "year", None) or "",
                "authors": getattr(f, "authors", None) or "",
            }
            for f in files
        ]
        analysis_by_file: dict[int, dict] = {}
        if PaperAnalysis is not None and files:
            fids = [int(f.id) for f in files]
            pa_rows = list(
                db.execute(select(PaperAnalysis).where(PaperAnalysis.file_id.in_(fids))).scalars().all()
            )
            for pa in pa_rows:
                raw = getattr(pa, "data", None) or "{}"
                try:
                    data = json.loads(raw) if isinstance(raw, str) else (raw or {})
                except Exception:
                    data = {}
                if isinstance(data, dict):
                    analysis_by_file[int(pa.file_id)] = data
        return papers, objects, analysis_by_file

    @bp.get("/api/projects/<int:project_id>/evidence/graph")
    @login_required
    def evidence_graph(project_id: int):
        """RI-005 — Project knowledge graph over Evidence (+ themes)."""
        uid = _uid()
        file_ids_raw = (request.args.get("file_ids") or "").strip()
        status_filter = (request.args.get("status") or "").strip()
        include_conflict = (request.args.get("include_conflict") or "1").strip() not in {
            "0",
            "false",
            "no",
        }
        db = SessionLocal()
        try:
            papers, objects, _analysis = _load_project_corpus(
                db,
                uid=uid,
                project_id=project_id,
                file_ids_raw=file_ids_raw,
                status_filter=status_filter,
            )
            themes = discover_themes(objects, project_id=project_id)
            conflict_links = []
            if include_conflict and objects:
                conflict = analyze_conflicts(objects)
                conflict_links = list(conflict.get("links") or [])
            payload = build_project_graph(
                project_id=project_id,
                papers=papers,
                evidence_objects=objects,
                themes_payload=themes,
                conflict_links=conflict_links,
            )
            return jsonify(payload)
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.get("/api/projects/<int:project_id>/evidence/gaps")
    @login_required
    def evidence_gaps(project_id: int):
        """RI-006 — Research gaps from themes + matrix (+ consensus/conflict)."""
        from flask import Response

        uid = _uid()
        fmt = (request.args.get("format") or "json").strip().lower()
        if fmt not in {"json", "markdown", "md"}:
            return (
                jsonify(
                    {
                        "error": ErrorCode.VALIDATION,
                        "detail": "format must be json or markdown",
                    }
                ),
                422,
            )
        if fmt == "md":
            fmt = "markdown"
        file_ids_raw = (request.args.get("file_ids") or "").strip()
        status_filter = (request.args.get("status") or "").strip()
        db = SessionLocal()
        try:
            papers, objects, analysis_by_file = _load_project_corpus(
                db,
                uid=uid,
                project_id=project_id,
                file_ids_raw=file_ids_raw,
                status_filter=status_filter,
            )
            themes = discover_themes(objects, project_id=project_id)
            evidence_by_file: dict[int, list] = {int(p["file_id"]): [] for p in papers}
            for o in objects:
                if o.get("file_id") is None:
                    continue
                fid = int(o["file_id"])
                evidence_by_file.setdefault(fid, []).append(o)
            matrix = build_evidence_matrix(
                project_id=project_id,
                papers=papers,
                evidence_by_file=evidence_by_file,
                analysis_by_file=analysis_by_file,
            )
            consensus = aggregate_consensus(objects) if objects else None
            conflict = analyze_conflicts(objects) if objects else None
            payload = discover_gaps(
                project_id=project_id,
                papers=papers,
                evidence_objects=objects,
                analysis_by_file=analysis_by_file,
                themes_payload=themes,
                matrix_payload=matrix,
                consensus_payload=consensus,
                conflict_payload=conflict,
            )
            if fmt == "markdown":
                body = gaps_to_markdown(payload)
                return Response(
                    body,
                    mimetype="text/markdown; charset=utf-8",
                    headers={
                        "Content-Disposition": (
                            f'attachment; filename="evidence-gaps-p{project_id}.md"'
                        )
                    },
                )
            return jsonify(payload)
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.get("/api/projects/<int:project_id>/evidence/timeline")
    @login_required
    def evidence_timeline(project_id: int):
        """RI-007 — Research timeline by year with paper/evidence/theme anchors."""
        from flask import Response

        uid = _uid()
        fmt = (request.args.get("format") or "json").strip().lower()
        if fmt not in {"json", "markdown", "md"}:
            return (
                jsonify(
                    {
                        "error": ErrorCode.VALIDATION,
                        "detail": "format must be json or markdown",
                    }
                ),
                422,
            )
        if fmt == "md":
            fmt = "markdown"
        file_ids_raw = (request.args.get("file_ids") or "").strip()
        status_filter = (request.args.get("status") or "").strip()
        db = SessionLocal()
        try:
            papers, objects, _analysis = _load_project_corpus(
                db,
                uid=uid,
                project_id=project_id,
                file_ids_raw=file_ids_raw,
                status_filter=status_filter,
            )
            themes = discover_themes(objects, project_id=project_id)
            payload = build_timeline(
                project_id=project_id,
                papers=papers,
                evidence_objects=objects,
                themes_payload=themes,
            )
            if fmt == "markdown":
                body = timeline_to_markdown(payload)
                return Response(
                    body,
                    mimetype="text/markdown; charset=utf-8",
                    headers={
                        "Content-Disposition": (
                            f'attachment; filename="evidence-timeline-p{project_id}.md"'
                        )
                    },
                )
            return jsonify(payload)
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.get("/api/projects/<int:project_id>/evidence/methodology")
    @login_required
    def evidence_methodology(project_id: int):
        """RI-008 — Methodology advisory cards grounded in Evidence."""
        from flask import Response

        uid = _uid()
        fmt = (request.args.get("format") or "json").strip().lower()
        if fmt not in {"json", "markdown", "md"}:
            return (
                jsonify(
                    {
                        "error": ErrorCode.VALIDATION,
                        "detail": "format must be json or markdown",
                    }
                ),
                422,
            )
        if fmt == "md":
            fmt = "markdown"
        file_ids_raw = (request.args.get("file_ids") or "").strip()
        status_filter = (request.args.get("status") or "").strip()
        db = SessionLocal()
        try:
            papers, objects, analysis_by_file = _load_project_corpus(
                db,
                uid=uid,
                project_id=project_id,
                file_ids_raw=file_ids_raw,
                status_filter=status_filter,
            )
            themes = discover_themes(objects, project_id=project_id)
            evidence_by_file: dict[int, list] = {int(p["file_id"]): [] for p in papers}
            for o in objects:
                if o.get("file_id") is None:
                    continue
                evidence_by_file.setdefault(int(o["file_id"]), []).append(o)
            matrix = build_evidence_matrix(
                project_id=project_id,
                papers=papers,
                evidence_by_file=evidence_by_file,
                analysis_by_file=analysis_by_file,
            )
            consensus = aggregate_consensus(objects) if objects else None
            conflict = analyze_conflicts(objects) if objects else None
            gaps = discover_gaps(
                project_id=project_id,
                papers=papers,
                evidence_objects=objects,
                analysis_by_file=analysis_by_file,
                themes_payload=themes,
                matrix_payload=matrix,
                consensus_payload=consensus,
                conflict_payload=conflict,
            )
            payload = build_methodology_advice(
                project_id=project_id,
                papers=papers,
                evidence_objects=objects,
                analysis_by_file=analysis_by_file,
                themes_payload=themes,
                matrix_payload=matrix,
                gaps_payload=gaps,
                consensus_payload=consensus,
            )
            if fmt == "markdown":
                body = methodology_to_markdown(payload)
                return Response(
                    body,
                    mimetype="text/markdown; charset=utf-8",
                    headers={
                        "Content-Disposition": (
                            f'attachment; filename="evidence-methodology-p{project_id}.md"'
                        )
                    },
                )
            return jsonify(payload)
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
            # Phase A.2: every review is also a persistent Research Decision
            decision = ResearchDecision(
                user_id=uid,
                project_id=row.project_id,
                evidence_object_id=row.id,
                decision_type=decision_type_from_review_status(payload["status"]),
                reason=payload["reason"],
                reason_code=(data.get("reason_code") or "")[:120],
                created_at=datetime.now(timezone.utc),
            )
            db.add(decision)
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
                db.flush()
                _emit_contract_event(
                    db,
                    aggregate_type="evidence_object",
                    aggregate_id=new_row.id,
                    event_type="EvidenceUpdated",
                    payload={
                        "evidence_object_id": new_row.id,
                        "status": "accepted",
                        "supersedes_id": row.id,
                    },
                )
            else:
                row.status = next_object_status_after_review(payload["status"])
                _emit_contract_event(
                    db,
                    aggregate_type="evidence_object",
                    aggregate_id=row.id,
                    event_type="EvidenceUpdated",
                    payload={"evidence_object_id": row.id, "status": row.status},
                )
            row.updated_at = datetime.now(timezone.utc)
            if WorkflowEvent is not None:
                from backend.workflow.routes import persist_workflow_event

                persist_workflow_event(
                    db,
                    WorkflowEvent=WorkflowEvent,
                    user_id=uid,
                    project_id=int(row.project_id),
                    event=(
                        "evidence_accepted"
                        if payload["status"] == "accepted"
                        else "evidence_rejected"
                        if payload["status"] == "rejected"
                        else "decision_recorded"
                    ),
                    meta={"evidence_id": evidence_id, "review_status": payload["status"]},
                )
            db.commit()
            log_evidence_metric("review", user_id=uid, evidence_id=evidence_id, status=payload["status"])
            return jsonify({"ok": True, "evidence": serialize_evidence_object(row if payload["status"] != "edited" else new_row)})
        except ValueError as exc:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": str(exc)}), 422
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.get("/api/projects/<int:project_id>/research-decisions")
    @login_required
    @limiter.limit("120 per hour")
    def list_research_decisions(project_id: int):
        """Activity feed of researcher decisions (Phase A.2). Quiet accumulation — not a dashboard."""
        uid = _uid()
        limit = min(max(int(request.args.get("limit") or 40), 1), 100)
        db = SessionLocal()
        try:
            require_owned_project(db, Project, user_id=uid, project_id=project_id)
            rows = (
                db.execute(
                    select(ResearchDecision)
                    .where(
                        ResearchDecision.user_id == uid,
                        ResearchDecision.project_id == project_id,
                    )
                    .order_by(ResearchDecision.created_at.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            eids = [int(r.evidence_object_id) for r in rows]
            claim_by_id: dict[int, str] = {}
            if eids:
                eos = (
                    db.execute(select(EvidenceObject).where(EvidenceObject.id.in_(eids)))
                    .scalars()
                    .all()
                )
                for eo in eos:
                    claim_by_id[int(eo.id)] = (eo.claim or eo.quote or "")[:240]
            items = [
                serialize_decision(
                    r,
                    claim_preview=claim_by_id.get(int(r.evidence_object_id), ""),
                )
                for r in rows
            ]
            return jsonify(
                {
                    "items": items,
                    "labels": DECISION_LABELS,
                    "reason_presets": REASON_PRESETS,
                }
            )
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.post("/api/projects/<int:project_id>/research-decisions")
    @login_required
    @limiter.limit("120 per hour")
    def create_research_decision(project_id: int):
        """Record IMPORTANT / Needs Review / Contradiction without requiring EO status flip."""
        uid = _uid()
        data = request.get_json(silent=True) or {}
        db = SessionLocal()
        try:
            require_owned_project(db, Project, user_id=uid, project_id=project_id)
            payload = validate_decision_payload(data)
            ev = require_owned_evidence(
                db, EvidenceObject, user_id=uid, evidence_id=payload["evidence_id"]
            )
            if int(ev.project_id) != int(project_id):
                raise EvidenceDomainError(ErrorCode.NOT_FOUND, "evidence_not_in_project")

            # ACCEPT/REJECT also update EvidenceObject status (same as reviews)
            if payload["type"] == "ACCEPT":
                ev.status = "accepted"
                ev.updated_at = datetime.now(timezone.utc)
            elif payload["type"] == "REJECT":
                ev.status = "rejected"
                ev.updated_at = datetime.now(timezone.utc)

            decision = ResearchDecision(
                user_id=uid,
                project_id=project_id,
                evidence_object_id=ev.id,
                decision_type=payload["type"],
                reason=payload["reason"],
                reason_code=payload.get("reason_code") or "",
                created_at=datetime.now(timezone.utc),
            )
            db.add(decision)
            if payload["type"] in ("ACCEPT", "REJECT"):
                db.add(
                    ClaimReview(
                        evidence_object_id=ev.id,
                        user_id=uid,
                        project_id=project_id,
                        status="accepted" if payload["type"] == "ACCEPT" else "rejected",
                        reason=payload["reason"],
                        reviewed_at=datetime.now(timezone.utc),
                    )
                )
                _emit_contract_event(
                    db,
                    aggregate_type="evidence_object",
                    aggregate_id=ev.id,
                    event_type="EvidenceUpdated",
                    payload={"evidence_object_id": ev.id, "status": ev.status},
                )
            db.commit()
            log_evidence_metric(
                "research_decision",
                user_id=uid,
                evidence_id=ev.id,
                status=payload["type"],
            )
            return jsonify(
                {
                    "ok": True,
                    "decision": serialize_decision(
                        decision,
                        claim_preview=(ev.claim or ev.quote or "")[:240],
                    ),
                    "evidence": serialize_evidence_object(ev),
                }
            ), 201
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
            db.flush()
            _emit_contract_event(
                db,
                aggregate_type="binding",
                aggregate_id=binding.id,
                event_type="BindingCreated",
                payload={
                    "binding_id": binding.id,
                    "document_id": doc.id,
                    "evidence_object_id": ev.id,
                },
            )
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
            _emit_contract_event(
                db,
                aggregate_type="binding",
                aggregate_id=row.id,
                event_type="BindingDeleted",
                payload={
                    "binding_id": row.id,
                    "document_id": row.document_id,
                    "evidence_object_id": row.evidence_object_id,
                },
            )
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
        """Enqueue Evidence Extraction (async). Returns 202 + job_id/run_id.

        Preflight gates (no job created):
          - 400 not_research_ready
          - 409 missing_phase1
          - 409 already_running

        Body `sync: true` keeps the legacy synchronous path (tests / no-worker).
        """
        from backend.evidence.provenance import compute_input_content_hash
        from backend.library.readiness import research_readiness

        uid = _uid()
        if ai_gate is not None:
            from security.ops.gate import AiAccessDenied

            try:
                ai_gate.preflight(
                    uid,
                    token_estimate=6_000,
                    cost_estimate=0.06,
                    operation="evidence_extract",
                    project_id=project_id,
                )
            except AiAccessDenied as exc:
                body = {"error": exc.code, "detail": exc.message}
                if getattr(exc, "payload", None):
                    body["quota"] = exc.payload
                return jsonify(body), exc.http_status
        data = request.get_json(silent=True) or {}
        file_id = data.get("file_id")
        force = bool(data.get("force"))
        sync = bool(data.get("sync"))
        if not file_id:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": "file_id required"}), 422
        db = SessionLocal()
        try:
            require_owned_project(db, Project, user_id=uid, project_id=project_id)
            uf = require_owned_file(
                db, UserFile, user_id=uid, file_id=int(file_id), project_id=project_id
            )

            readiness = research_readiness(uf)
            if readiness != "research_ready":
                run = EvidenceExtractionRun(
                    user_id=uid,
                    project_id=project_id,
                    file_id=int(file_id),
                    pipeline_version=PIPELINE_VERSION,
                    input_content_hash="not_ready",
                    status="skipped",
                    objects_created=0,
                    error_json=json.dumps(
                        {"reason": "not_research_ready", "readiness": readiness}
                    ),
                    finished_at=datetime.now(timezone.utc),
                )
                db.add(run)
                db.commit()
                return (
                    jsonify(
                        {
                            "error": "not_research_ready",
                            "detail": "Paper must be Research Ready before Evidence Extraction.",
                            "status": "skipped",
                            "reason": "not_research_ready",
                            "objects_created": 0,
                            "run_id": run.id,
                            "job_id": None,
                            "pipeline_version": PIPELINE_VERSION,
                        }
                    ),
                    400,
                )

            analysis = load_analysis_result(db, AnalysisPipelineResult, int(file_id))
            if not analysis or not analysis.phase_results:
                run = EvidenceExtractionRun(
                    user_id=uid,
                    project_id=project_id,
                    file_id=int(file_id),
                    pipeline_version=PIPELINE_VERSION,
                    input_content_hash="missing_phase1",
                    status="skipped",
                    objects_created=0,
                    error_json=json.dumps({"reason": "missing_phase1"}),
                    finished_at=datetime.now(timezone.utc),
                )
                db.add(run)
                db.commit()
                return (
                    jsonify(
                        {
                            "error": "missing_phase1",
                            "detail": "Document understanding is not complete yet.",
                            "status": "skipped",
                            "reason": "missing_phase1",
                            "objects_created": 0,
                            "run_id": run.id,
                            "job_id": None,
                            "pipeline_version": PIPELINE_VERSION,
                        }
                    ),
                    409,
                )

            # Legacy sync path (explicit, or when no queue wire-up).
            if sync or enqueue_job is None:
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
                    OutboxEvent=OutboxEvent,
                )
                return jsonify({**result, "job_id": None, "pipeline_version": PIPELINE_VERSION})

            file_fp = analysis.content_hash or getattr(uf, "content_hash", "") or f"file:{file_id}"
            input_hash = compute_input_content_hash(
                file_fingerprint=file_fp,
                document_understanding_version=str(
                    (analysis.phase_results.get("document_understanding") or {}).get(
                        "pipeline_version"
                    )
                    or ""
                ),
                evidence_grading_version=str(
                    (analysis.phase_results.get("evidence_grading") or {}).get("pipeline_version")
                    or ""
                ),
                knowledge_graph_version=str(
                    (analysis.phase_results.get("knowledge_graph") or {}).get("pipeline_version")
                    or (analysis.phase_results.get("knowledge_graph") or {}).get("version")
                    or ""
                ),
                extraction_prompt_version=EXTRACTION_PROMPT_VERSION,
                pipeline_version=PIPELINE_VERSION,
            )

            if not force:
                prior = db.execute(
                    select(EvidenceExtractionRun).where(
                        EvidenceExtractionRun.project_id == project_id,
                        EvidenceExtractionRun.file_id == int(file_id),
                        EvidenceExtractionRun.pipeline_version == PIPELINE_VERSION,
                        EvidenceExtractionRun.input_content_hash == input_hash,
                        EvidenceExtractionRun.status == "succeeded",
                    )
                ).scalar_one_or_none()
                if prior:
                    return jsonify(
                        {
                            "status": "succeeded",
                            "reason": "idempotent_reuse",
                            "objects_created": prior.objects_created or 0,
                            "run_id": prior.id,
                            "job_id": prior.job_id,
                            "pipeline_version": PIPELINE_VERSION,
                        }
                    )

                active = db.execute(
                    select(UploadJob)
                    .where(
                        UploadJob.user_id == uid,
                        UploadJob.file_id == int(file_id),
                        UploadJob.job_type == "evidence_extract",
                        UploadJob.status.in_(("pending", "running")),
                    )
                    .order_by(UploadJob.id.desc())
                    .limit(1)
                ).scalar_one_or_none()
                if active:
                    return (
                        jsonify(
                            {
                                "error": "already_running",
                                "detail": "Evidence Extraction is already queued or running for this paper.",
                                "status": active.status,
                                "job_id": active.id,
                                "pipeline_version": PIPELINE_VERSION,
                            }
                        ),
                        409,
                    )

            run = EvidenceExtractionRun(
                user_id=uid,
                project_id=project_id,
                file_id=int(file_id),
                pipeline_version=PIPELINE_VERSION,
                input_content_hash=input_hash,
                status="queued",
                objects_created=0,
            )
            db.add(run)
            db.flush()

            job = UploadJob(
                file_id=int(file_id),
                user_id=uid,
                job_type="evidence_extract",
                status="pending",
            )
            db.add(job)
            db.flush()
            run.job_id = job.id
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
                            "already_applied": False,
                            "run_id": run.id,
                        }
                    ),
                )
            )
            _emit_contract_event(
                db,
                aggregate_type="evidence_extraction_run",
                aggregate_id=run.id,
                event_type="EvidenceExtractionStarted",
                payload={
                    "run_id": run.id,
                    "project_id": project_id,
                    "paper_id": int(file_id),
                    "job_id": job.id,
                },
            )
            db.commit()
            log_evidence_metric(
                "extraction_enqueued",
                user_id=uid,
                project_id=project_id,
                file_id=int(file_id),
                job_id=job.id,
                run_id=run.id,
                pipeline_version=PIPELINE_VERSION,
            )
            return (
                jsonify(
                    {
                        "job_id": job.id,
                        "run_id": run.id,
                        "status": "pending",
                        "pipeline_version": PIPELINE_VERSION,
                    }
                ),
                202,
            )
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

    def _normalize_and_authorize_query(db, *, user_id: int, data: dict[str, Any]) -> tuple[dict[str, Any], int | None]:
        """Shared EvidenceQuery parse + scope ownership checks for RI routes."""
        raw = data.get("query") if isinstance(data.get("query"), dict) else data
        query = normalize_evidence_query(raw, user_id=user_id)
        project_id = int(query["scope"]["project_id"])
        require_owned_project(db, Project, user_id=user_id, project_id=project_id)
        doc_id = query["scope"].get("document_id")
        if doc_id is not None:
            doc = require_owned_document(db, WritingDocument, user_id=user_id, document_id=int(doc_id))
            if int(doc.project_id) != project_id:
                raise EvidenceDomainError(ErrorCode.NOT_FOUND, "document_not_in_project")
            return query, int(doc_id)
        return query, None

    def _run_retrieval():
        uid = _uid()
        data = request.get_json(silent=True) or {}
        started = time.perf_counter()
        db = SessionLocal()
        try:
            query, _doc_id = _normalize_and_authorize_query(db, user_id=uid, data=data)
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
            return _json_ri(result, started=started)
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
        started = time.perf_counter()
        db = SessionLocal()
        try:
            query, _doc_id = _normalize_and_authorize_query(db, user_id=uid, data=data)
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
            return _json_ri(result, started=started)
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
        started = time.perf_counter()
        db = SessionLocal()
        try:
            query, doc_id = _normalize_and_authorize_query(db, user_id=uid, data=data)
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
            return _json_ri(result, started=started)
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

    def _run_conflict():
        """Conflict stage: EvidenceQuery → … → Consensus → coded mediators."""
        uid = _uid()
        data = request.get_json(silent=True) or {}
        started = time.perf_counter()
        db = SessionLocal()
        try:
            query, doc_id = _normalize_and_authorize_query(db, user_id=uid, data=data)
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
            consensus = apply_consensus_stage(ranked, binding_relations=relations)
            result = apply_conflict_stage(consensus, binding_relations=relations)
            log_evidence_metric(
                "conflict",
                user_id=uid,
                project_id=query["scope"]["project_id"],
                intent=query["intent"],
                has_conflict=(result.get("conflict") or {}).get("has_conflict"),
                mediators=len((result.get("conflict") or {}).get("mediators") or []),
                pair_count=(result.get("conflict") or {}).get("pair_count"),
            )
            return _json_ri(result, started=started)
        except ValueError as exc:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": str(exc)}), 422
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.post("/api/evidence/conflict")
    @login_required
    @limiter.limit("120 per hour")
    def evidence_conflict():
        """Conflict stage: coded mediators between supporting and contradicting objects."""
        return _run_conflict()

    def _run_reasoning():
        """Reasoning stage: full pipeline through Conflict, then structured chain."""
        uid = _uid()
        data = request.get_json(silent=True) or {}
        started = time.perf_counter()
        db = SessionLocal()
        try:
            query, doc_id = _normalize_and_authorize_query(db, user_id=uid, data=data)
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
            consensus = apply_consensus_stage(ranked, binding_relations=relations)
            conflicted = apply_conflict_stage(consensus, binding_relations=relations)
            result = apply_reasoning_stage(conflicted)
            log_evidence_metric(
                "reasoning",
                user_id=uid,
                project_id=query["scope"]["project_id"],
                intent=query["intent"],
                summary_code=(result.get("reasoning") or {}).get("summary_code"),
                sufficiency=(result.get("reasoning") or {}).get("sufficiency"),
                steps=len((result.get("reasoning") or {}).get("steps") or []),
            )
            return _json_ri(result, started=started)
        except ValueError as exc:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": str(exc)}), 422
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.post("/api/evidence/reason")
    @login_required
    @limiter.limit("120 per hour")
    def evidence_reason():
        """Reasoning stage: structured chain from prior RI stages (no generation)."""
        return _run_reasoning()

    def _enrich_writing_bibliography(db, *, uid: int, writing: dict[str, Any]) -> dict[str, Any]:
        """Attach paper bibliographic fields onto bibliography/citation rows (Phase A.4)."""
        if not isinstance(writing, dict):
            return writing
        rows = list(writing.get("bibliography") or []) + list(writing.get("citations") or [])
        file_ids = {
            int(r["file_id"])
            for r in rows
            if r.get("file_id") is not None
        }
        if not file_ids:
            return writing
        files = (
            db.execute(
                select(UserFile).where(
                    UserFile.user_id == uid,
                    UserFile.id.in_(sorted(file_ids)),
                )
            )
            .scalars()
            .all()
        )
        meta_by_id = {
            int(f.id): {
                "paper_title": (f.title or f.name or "")[:500],
                "authors": (getattr(f, "authors", None) or "")[:500],
                "year": (getattr(f, "year", None) or "")[:20],
                "venue": (getattr(f, "venue", None) or "")[:300],
                "doi": (getattr(f, "doi", None) or "")[:200],
            }
            for f in files
        }

        def _enrich(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            out: list[dict[str, Any]] = []
            for item in items:
                enriched = dict(item)
                fid = item.get("file_id")
                if fid is not None and int(fid) in meta_by_id:
                    enriched.update(meta_by_id[int(fid)])
                out.append(enriched)
            return out

        writing = dict(writing)
        if writing.get("bibliography"):
            writing["bibliography"] = _enrich(list(writing["bibliography"]))
        if writing.get("citations"):
            writing["citations"] = _enrich(list(writing["citations"]))
        sections = []
        for sec in list(writing.get("sections") or []):
            s = dict(sec)
            if s.get("bindings"):
                s["bindings"] = _enrich(list(s["bindings"]))
            if s.get("citations"):
                s["citations"] = _enrich(list(s["citations"]))
            sections.append(s)
        if sections:
            writing["sections"] = sections
        return writing

    def _run_writing_intelligence():
        """Writing Intelligence: full RI pipeline, generation last (grounded_v1 / RI-009)."""
        uid = _uid()
        if feature_flag_service is not None:
            if not feature_flag_service.is_enabled(writing_intelligence_flag, user_id=uid):
                return (
                    jsonify(
                        {
                            "error": "feature_disabled",
                            "flag": writing_intelligence_flag,
                            "detail": "Writing Intelligence is temporarily disabled.",
                        }
                    ),
                    503,
                )
        if ai_gate is not None:
            from security.ops.gate import AiAccessDenied

            try:
                ai_gate.preflight(
                    uid,
                    token_estimate=8_000,
                    cost_estimate=0.08,
                    operation="writing_intelligence",
                )
            except AiAccessDenied as exc:
                body = {"error": exc.code, "detail": exc.message}
                if getattr(exc, "payload", None):
                    body["quota"] = exc.payload
                return jsonify(body), exc.http_status
        data = request.get_json(silent=True) or {}
        started = time.perf_counter()
        db = SessionLocal()
        try:
            query, doc_id = _normalize_and_authorize_query(db, user_id=uid, data=data)
            # Phase A.3: Writing drafts must never silently use candidate evidence.
            filters = dict(query.get("filters") or {})
            filters["status"] = ["accepted"]
            query = {**query, "filters": filters}
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
            consensus = apply_consensus_stage(ranked, binding_relations=relations)
            conflicted = apply_conflict_stage(consensus, binding_relations=relations)
            reasoned = apply_reasoning_stage(conflicted)
            composer = None
            if ai_gateway is not None and get_model_registry is not None:
                from backend.evidence.writing.gateway_composer import make_gateway_composer

                section_type = str((query.get("section_type") or "")).strip().lower()
                task = (
                    "literature_review"
                    if section_type == "literature_review"
                    else "section_generator"
                )
                composer = make_gateway_composer(
                    ai_gateway=ai_gateway,
                    model_registry=get_model_registry(db),
                    mode=writing_quality_mode,
                    user_id=uid,
                    task=task,
                )
            result = apply_writing_intelligence_stage(reasoned, composer=composer)
            writing = result.get("writing") or {}
            # Phase A.4: enrich bibliography with real paper metadata for citation export
            writing = _enrich_writing_bibliography(db, uid=uid, writing=writing)
            result["writing"] = writing
            review = writing.get("review")
            # Persist when scoped to a document so history is reconstructable (A-401 / A-503).
            if doc_id is not None and isinstance(review, dict):
                doc = require_owned_document(
                    db, WritingDocument, user_id=uid, document_id=int(doc_id)
                )
                run = persist_reviewer_run(
                    db,
                    ReviewerRun=ReviewerRun,
                    ReviewerFinding=ReviewerFinding,
                    user_id=uid,
                    project_id=int(query["scope"]["project_id"]),
                    document_id=int(doc_id),
                    document_version_no=int(doc.current_version or 1),
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
                    },
                )
                _emit_contract_event(
                    db,
                    aggregate_type="document",
                    aggregate_id=int(doc_id),
                    event_type="ReviewCompleted",
                    payload={
                        "document_id": int(doc_id),
                        "reviewer_run_id": int(run.id),
                        "reviewer_version": review.get("reviewer_version"),
                        "issue_count": int(review.get("issue_count") or 0),
                        "metrics": review.get("metrics") or {},
                        "status": review.get("status"),
                    },
                )
                db.commit()
                writing["reviewer_run_id"] = int(run.id)
                result["writing"] = writing
            log_evidence_metric(
                "writing_intelligence",
                user_id=uid,
                project_id=query["scope"]["project_id"],
                intent=query["intent"],
                status=writing.get("status"),
                blocked_reason=writing.get("blocked_reason"),
                citations=len(writing.get("citations") or []),
            )
            if WorkflowEvent is not None and writing.get("status") == "ok":
                from backend.workflow.routes import persist_workflow_event

                persist_workflow_event(
                    db,
                    WorkflowEvent=WorkflowEvent,
                    user_id=uid,
                    project_id=int(query["scope"]["project_id"]),
                    event="draft_generated",
                    meta={
                        "section_type": writing.get("section_type"),
                        "citations": len(writing.get("citations") or []),
                        "document_id": int(doc_id) if doc_id is not None else None,
                    },
                )
                db.commit()
            return _json_ri(result, started=started)
        except ValueError as exc:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": str(exc)}), 422
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.post("/api/evidence/writing")
    @login_required
    @limiter.limit("60 per hour")
    def evidence_writing():
        """Writing Intelligence: grounded generation after RI pipeline (Sprint 6)."""
        return _run_writing_intelligence()

    def _load_run_with_findings(db, *, run_id: int, user_id: int):
        run = db.execute(select(ReviewerRun).where(ReviewerRun.id == int(run_id))).scalar_one_or_none()
        if run is None or int(run.user_id) != int(user_id):
            raise EvidenceDomainError(ErrorCode.NOT_FOUND, "reviewer_run_not_found")
        require_owned_document(db, WritingDocument, user_id=user_id, document_id=int(run.document_id))
        findings = (
            db.execute(
                select(ReviewerFinding)
                .where(ReviewerFinding.run_id == int(run.id))
                .order_by(ReviewerFinding.id.asc())
            )
            .scalars()
            .all()
        )
        return run, findings

    @bp.get("/api/documents/<int:document_id>/reviewer-runs")
    @login_required
    def list_reviewer_runs(document_id: int):
        """List durable reviewer runs for a writing document (newest first)."""
        uid = _uid()
        db = SessionLocal()
        try:
            require_owned_document(db, WritingDocument, user_id=uid, document_id=document_id)
            try:
                limit = int(request.args.get("limit") or 20)
            except ValueError:
                return jsonify({"error": ErrorCode.VALIDATION, "detail": "limit must be an integer"}), 422
            limit = max(1, min(100, limit))
            rows = (
                db.execute(
                    select(ReviewerRun)
                    .where(
                        ReviewerRun.document_id == int(document_id),
                        ReviewerRun.user_id == uid,
                    )
                    .order_by(ReviewerRun.created_at.desc(), ReviewerRun.id.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            return jsonify(
                {
                    "document_id": int(document_id),
                    "items": [serialize_run(r) for r in rows],
                    "count": len(rows),
                }
            )
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.get("/api/documents/<int:document_id>/reviewer-runs/latest")
    @login_required
    def latest_reviewer_run(document_id: int):
        """Return the newest reconstructable reviewer run for a document."""
        uid = _uid()
        db = SessionLocal()
        try:
            require_owned_document(db, WritingDocument, user_id=uid, document_id=document_id)
            run = (
                db.execute(
                    select(ReviewerRun)
                    .where(
                        ReviewerRun.document_id == int(document_id),
                        ReviewerRun.user_id == uid,
                    )
                    .order_by(ReviewerRun.created_at.desc(), ReviewerRun.id.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if run is None:
                raise EvidenceDomainError(ErrorCode.NOT_FOUND, "reviewer_run_not_found")
            findings = (
                db.execute(
                    select(ReviewerFinding)
                    .where(ReviewerFinding.run_id == int(run.id))
                    .order_by(ReviewerFinding.id.asc())
                )
                .scalars()
                .all()
            )
            return jsonify(serialize_run(run, findings=findings))
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.get("/api/reviewer-runs/<int:run_id>")
    @login_required
    def get_reviewer_run(run_id: int):
        """Reconstruct a historical review by run id (findings + input snapshot)."""
        uid = _uid()
        db = SessionLocal()
        try:
            run, findings = _load_run_with_findings(db, run_id=run_id, user_id=uid)
            return jsonify(serialize_run(run, findings=findings))
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    return bp
