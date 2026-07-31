"""Research Engine HTTP routes — W5 structured extract + W6 research jobs."""

from __future__ import annotations

import json
from typing import Any, Callable

from flask import Blueprint, Response, jsonify, request, session

from backend.evidence.api.errors import ErrorCode, EvidenceDomainError
from backend.evidence.objects import serialize_evidence_object
from backend.evidence.query import normalize_evidence_query
from backend.evidence.services.permission_service import (
    require_owned_document,
    require_owned_file,
    require_owned_project,
)
from backend.research.jobs import (
    load_research_job_result,
    run_literature_review_job,
    run_theme_map_job,
)
from backend.research.structured_extract import (
    build_structured_extract_table,
    table_to_csv,
    table_to_markdown,
)


def create_research_blueprint(
    *,
    SessionLocal: Any,
    Project: Any,
    UserFile: Any,
    WritingDocument: Any,
    EvidenceObject: Any,
    WritingSentenceBinding: Any,
    ReviewerRun: Any,
    ReviewerFinding: Any,
    AnalysisPipelineResult: Any,
    UploadJob: Any,
    OutboxEvent: Any,
    PaperAnalysis: Any | None,
    select: Any,
    login_required: Callable,
    limiter: Any,
    load_analysis_result: Callable,
    enqueue_job: Callable | None = None,
    ai_gateway: Any | None = None,
    get_model_registry: Callable | None = None,
    writing_quality_mode: str = "grounded_v1",
) -> Blueprint:
    bp = Blueprint("research_engine", __name__)

    def _uid() -> int:
        return int(session["user_id"])

    def _err(exc: EvidenceDomainError):
        status = 404 if exc.code == ErrorCode.NOT_FOUND else 403 if exc.code == ErrorCode.AUTHZ_DENIED else 422
        return jsonify({"error": exc.code, "detail": exc.detail}), status

    def _paper_title(f: Any) -> str:
        return (getattr(f, "title", None) or getattr(f, "name", None) or f"#{f.id}")[:500]

    def _binding_relation_map(db, *, user_id: int, project_id: int, document_id: int | None) -> dict[int, str]:
        if document_id is None or WritingSentenceBinding is None:
            return {}
        rows = (
            db.execute(
                select(WritingSentenceBinding).where(
                    WritingSentenceBinding.user_id == user_id,
                    WritingSentenceBinding.project_id == project_id,
                    WritingSentenceBinding.document_id == int(document_id),
                )
            )
            .scalars()
            .all()
        )
        return {
            int(b.evidence_object_id): (b.relation or "supports").strip().lower() for b in rows
        }

    def _enrich_writing_bibliography(db, *, uid: int, writing: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(writing, dict):
            return writing
        rows = list(writing.get("bibliography") or []) + list(writing.get("citations") or [])
        file_ids = {int(r["file_id"]) for r in rows if r.get("file_id") is not None}
        if not file_ids:
            return writing
        files = (
            db.execute(
                select(UserFile).where(UserFile.user_id == uid, UserFile.id.in_(sorted(file_ids)))
            )
            .scalars()
            .all()
        )
        meta_by_id = {
            int(f.id): {
                "paper_title": _paper_title(f),
                "authors": (getattr(f, "authors", None) or "")[:500],
                "year": (getattr(f, "year", None) or "")[:20],
                "venue": (getattr(f, "venue", None) or "")[:300],
                "doi": (getattr(f, "doi", None) or "")[:200],
            }
            for f in files
        }

        def _enrich(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            out = []
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
        return writing

    def _normalize_query(db, *, user_id: int, data: dict[str, Any]) -> tuple[dict[str, Any], int | None]:
        raw = data.get("query") if isinstance(data.get("query"), dict) else data
        query = normalize_evidence_query(raw, user_id=user_id)
        project_id = int(query["scope"]["project_id"])
        require_owned_project(db, Project, user_id=user_id, project_id=project_id)
        doc_id = query["scope"].get("document_id")
        if doc_id is not None:
            doc = require_owned_document(
                db, WritingDocument, user_id=user_id, document_id=int(doc_id)
            )
            if int(doc.project_id) != project_id:
                raise EvidenceDomainError(ErrorCode.NOT_FOUND, "document_not_in_project")
            return query, int(doc_id)
        return query, None

    def _build_table_for_project(db, *, uid: int, project_id: int, file_ids: list[int] | None):
        require_owned_project(db, Project, user_id=uid, project_id=project_id)
        file_q = select(UserFile).where(
            UserFile.user_id == uid,
            UserFile.project_id == project_id,
        )
        if file_ids:
            file_q = file_q.where(UserFile.id.in_(file_ids))
        files = list(db.execute(file_q.order_by(UserFile.id.asc())).scalars().all())

        evidence_by_file: dict[int, list] = {int(f.id): [] for f in files}
        if files:
            fids = [int(f.id) for f in files]
            ev_rows = list(
                db.execute(
                    select(EvidenceObject).where(
                        EvidenceObject.user_id == uid,
                        EvidenceObject.project_id == project_id,
                        EvidenceObject.file_id.in_(fids),
                        EvidenceObject.status.in_(["candidate", "accepted"]),
                    )
                )
                .scalars()
                .all()
            )
            for row in ev_rows:
                fid = int(row.file_id)
                if fid in evidence_by_file:
                    evidence_by_file[fid].append(serialize_evidence_object(row))

        papers: list[dict[str, Any]] = []
        for f in files:
            medical = None
            analysis = load_analysis_result(db, AnalysisPipelineResult, int(f.id))
            if analysis and isinstance(analysis.phase_results, dict):
                medical = analysis.phase_results.get("medical_understanding")
            title = _paper_title(f)
            year = str(getattr(f, "year", None) or "")
            if PaperAnalysis is not None:
                pa = db.execute(
                    select(PaperAnalysis).where(PaperAnalysis.file_id == int(f.id))
                ).scalar_one_or_none()
                if pa is not None:
                    title = getattr(pa, "title", None) or title
                    year = str(getattr(pa, "year", None) or year)
            papers.append(
                {
                    "file_id": int(f.id),
                    "paper_title": title,
                    "paper_year": year,
                    "medical": medical if isinstance(medical, dict) else None,
                    "evidence_objects": evidence_by_file.get(int(f.id), []),
                }
            )
        return build_structured_extract_table(project_id=project_id, papers=papers)

    @bp.get("/api/projects/<int:project_id>/research/extract-table")
    @login_required
    def project_extract_table(project_id: int):
        """W5 — PICO / methods / outcomes table + export formats."""
        uid = _uid()
        fmt = (request.args.get("format") or "json").strip().lower()
        if fmt == "md":
            fmt = "markdown"
        if fmt not in {"json", "markdown", "csv"}:
            return (
                jsonify(
                    {
                        "error": ErrorCode.VALIDATION,
                        "detail": "format must be json, markdown, or csv",
                    }
                ),
                422,
            )
        file_ids_raw = (request.args.get("file_ids") or "").strip()
        file_ids = None
        if file_ids_raw:
            try:
                file_ids = [int(x) for x in file_ids_raw.split(",") if x.strip()]
            except ValueError:
                return jsonify({"error": ErrorCode.VALIDATION, "detail": "file_ids invalid"}), 422

        db = SessionLocal()
        try:
            table = _build_table_for_project(
                db, uid=uid, project_id=project_id, file_ids=file_ids
            )
            if fmt == "markdown":
                body = table_to_markdown(table)
                return Response(
                    body,
                    mimetype="text/markdown; charset=utf-8",
                    headers={
                        "Content-Disposition": (
                            f'attachment; filename="structured-extract-p{project_id}.md"'
                        )
                    },
                )
            if fmt == "csv":
                body = table_to_csv(table)
                return Response(
                    body,
                    mimetype="text/csv; charset=utf-8",
                    headers={
                        "Content-Disposition": (
                            f'attachment; filename="structured-extract-p{project_id}.csv"'
                        )
                    },
                )
            return jsonify(table)
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.get("/api/files/<int:file_id>/research/extract-table")
    @login_required
    def file_extract_table(file_id: int):
        uid = _uid()
        fmt = (request.args.get("format") or "json").strip().lower()
        if fmt == "md":
            fmt = "markdown"
        if fmt not in {"json", "markdown", "csv"}:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": "format invalid"}), 422
        db = SessionLocal()
        try:
            uf = require_owned_file(db, UserFile, user_id=uid, file_id=int(file_id))
            project_id = int(uf.project_id) if uf.project_id is not None else None
            medical = None
            analysis = load_analysis_result(db, AnalysisPipelineResult, int(file_id))
            if analysis and isinstance(analysis.phase_results, dict):
                medical = analysis.phase_results.get("medical_understanding")
            title = _paper_title(uf)
            year = str(getattr(uf, "year", None) or "")
            if PaperAnalysis is not None:
                pa = db.execute(
                    select(PaperAnalysis).where(PaperAnalysis.file_id == int(file_id))
                ).scalar_one_or_none()
                if pa is not None:
                    title = getattr(pa, "title", None) or title
                    year = str(getattr(pa, "year", None) or year)
            ev_rows = list(
                db.execute(
                    select(EvidenceObject).where(
                        EvidenceObject.user_id == uid,
                        EvidenceObject.file_id == int(file_id),
                        EvidenceObject.status.in_(["candidate", "accepted"]),
                    )
                )
                .scalars()
                .all()
            )
            table = build_structured_extract_table(
                project_id=project_id,
                papers=[
                    {
                        "file_id": int(file_id),
                        "paper_title": title,
                        "paper_year": year,
                        "medical": medical if isinstance(medical, dict) else None,
                        "evidence_objects": [serialize_evidence_object(r) for r in ev_rows],
                    }
                ],
            )
            if fmt == "markdown":
                return Response(table_to_markdown(table), mimetype="text/markdown; charset=utf-8")
            if fmt == "csv":
                return Response(table_to_csv(table), mimetype="text/csv; charset=utf-8")
            return jsonify(table)
        except EvidenceDomainError as exc:
            return _err(exc)
        finally:
            db.close()

    @bp.post("/api/projects/<int:project_id>/research/jobs")
    @login_required
    @limiter.limit("30 per hour")
    def enqueue_research_job(project_id: int):
        """W6 — enqueue literature_review or theme_map (202 + job_id).

        Body ``sync: true`` runs inline (tests / no worker).
        """
        uid = _uid()
        data = request.get_json(silent=True) or {}
        kind = str(data.get("type") or data.get("kind") or "").strip().lower()
        if kind not in {"literature_review", "theme_map"}:
            return (
                jsonify(
                    {
                        "error": ErrorCode.VALIDATION,
                        "detail": "type must be literature_review or theme_map",
                    }
                ),
                422,
            )
        sync = bool(data.get("sync"))
        file_ids = data.get("file_ids")
        if file_ids is not None and not isinstance(file_ids, list):
            return jsonify({"error": ErrorCode.VALIDATION, "detail": "file_ids must be a list"}), 422

        db = SessionLocal()
        try:
            require_owned_project(db, Project, user_id=uid, project_id=project_id)

            if kind == "literature_review":
                query_body = data.get("query") if isinstance(data.get("query"), dict) else data
                if not isinstance(query_body, dict):
                    return jsonify({"error": ErrorCode.VALIDATION, "detail": "query must be object"}), 422
                scope = dict(query_body.get("scope") or {})
                scope["project_id"] = project_id
                query_body = {
                    **query_body,
                    "scope": scope,
                    "section_type": query_body.get("section_type") or "literature_review",
                    "intent": query_body.get("intent") or "support_sentence",
                }
                query, doc_id = _normalize_query(db, user_id=uid, data=query_body)

            if sync or enqueue_job is None:
                if kind == "theme_map":
                    result = run_theme_map_job(
                        db,
                        user_id=uid,
                        project_id=project_id,
                        EvidenceObject=EvidenceObject,
                        select=select,
                        file_ids=[int(x) for x in file_ids] if file_ids else None,
                    )
                else:
                    composer = None
                    if ai_gateway is not None and get_model_registry is not None:
                        from backend.evidence.writing.gateway_composer import make_gateway_composer

                        composer = make_gateway_composer(
                            ai_gateway=ai_gateway,
                            model_registry=get_model_registry(db),
                            mode=writing_quality_mode,
                            user_id=uid,
                            task="literature_review",
                        )
                    result = run_literature_review_job(
                        db,
                        user_id=uid,
                        query=query,
                        EvidenceObject=EvidenceObject,
                        WritingSentenceBinding=WritingSentenceBinding,
                        WritingDocument=WritingDocument,
                        ReviewerRun=ReviewerRun,
                        ReviewerFinding=ReviewerFinding,
                        select=select,
                        require_owned_document=require_owned_document,
                        enrich_bibliography=_enrich_writing_bibliography,
                        binding_relation_map=_binding_relation_map,
                        composer=composer,
                        writing_quality_mode=writing_quality_mode,
                    )
                return jsonify({"status": "done", "job_id": None, "type": kind, "result": result})

            # Anchor job on first project file when available (UploadJob.file_id nullable).
            anchor = (
                db.execute(
                    select(UserFile.id)
                    .where(UserFile.user_id == uid, UserFile.project_id == project_id)
                    .order_by(UserFile.id.asc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            job = UploadJob(
                file_id=int(anchor) if anchor is not None else None,
                user_id=uid,
                job_type=kind,
                status="pending",
            )
            db.add(job)
            db.flush()
            payload = {
                "project_id": project_id,
                "type": kind,
                "file_ids": [int(x) for x in file_ids] if file_ids else None,
            }
            if kind == "literature_review":
                payload["query"] = query
            db.add(
                OutboxEvent(
                    aggregate_type="upload_job",
                    aggregate_id=job.id,
                    event_type="job.enqueued",
                    payload=json.dumps(payload, ensure_ascii=False, default=str),
                )
            )
            db.commit()
            return (
                jsonify(
                    {
                        "status": "queued",
                        "job_id": job.id,
                        "type": kind,
                        "project_id": project_id,
                    }
                ),
                202,
            )
        except EvidenceDomainError as exc:
            return _err(exc)
        except Exception as exc:
            return jsonify({"error": ErrorCode.VALIDATION, "detail": str(exc)}), 422
        finally:
            db.close()

    @bp.get("/api/research/jobs/<int:job_id>")
    @login_required
    def get_research_job(job_id: int):
        """Poll research job status + result payload when done."""
        uid = _uid()
        db = SessionLocal()
        try:
            job = db.get(UploadJob, int(job_id))
            if job is None or int(job.user_id) != uid:
                return jsonify({"error": ErrorCode.NOT_FOUND, "detail": "job not found"}), 404
            if job.job_type not in ("literature_review", "theme_map"):
                return jsonify({"error": ErrorCode.VALIDATION, "detail": "not a research job"}), 422
            body: dict[str, Any] = {
                "job_id": job.id,
                "type": job.job_type,
                "status": job.status,
                "attempts": job.attempts,
                "last_error": job.last_error,
                "result": None,
            }
            if job.status == "done":
                stored = load_research_job_result(
                    db, OutboxEvent=OutboxEvent, select=select, job_id=job.id
                )
                if stored:
                    body["result"] = stored.get("result")
                    body["kind"] = stored.get("kind")
            return jsonify(body)
        finally:
            db.close()

    return bp
