"""HTTP routes for Phase 2 analysis pipeline.

POST /api/documents/<id>/analyze
GET  /api/documents/<id>/pipeline
GET  /api/documents/<id>/phases/<phase>
"""

from __future__ import annotations

import logging
import os
import tempfile

from flask import Blueprint, g, jsonify, request
from sqlalchemy import select

from auth.decorators import jwt_required

from .models import AnalysisOptions
from .persistence import load_analysis_result
from .service import AnalysisPipelineService, extract_bibliographic_fields
from .summary import build_phase1_prompt_context

log = logging.getLogger(__name__)

_VALID_PHASES = frozenset(
    {
        "document_understanding",
        "classification",
        "analysis_context",
        "medical_understanding",
        "evidence_grading",
        "prompt_assembly",
        "knowledge_graph",
    }
)


def create_analysis_pipeline_blueprint(
    *,
    SessionLocal,
    UserFile,
    UploadJob,
    OutboxEvent,
    AnalysisPipelineResult,
    enqueue_job,
    storage_backend,
):
    bp = Blueprint("analysis_pipeline", __name__, url_prefix="/api/documents")

    @bp.route("/<int:doc_id>/analyze", methods=["POST"])
    @jwt_required()
    def analyze_document(doc_id: int):
        """Trigger Phase 1 pipeline. Default: enqueue worker job. ?sync=1 runs inline."""
        user_id = int(g.current_user)
        body = request.get_json(silent=True) or {}
        sync = str(request.args.get("sync") or body.get("sync") or "").lower() in ("1", "true", "yes")
        force = bool(body.get("force", False))

        db = SessionLocal()
        try:
            uf = db.get(UserFile, doc_id)
            if not uf or uf.user_id != user_id:
                return jsonify({"error": "not_found", "message": "Document not found"}), 404

            if not sync:
                job_id = enqueue_job(db, user_id, doc_id, "phase1_analysis")
                db.commit()
                return (
                    jsonify(
                        {
                            "status": "queued",
                            "job_id": job_id,
                            "document_id": doc_id,
                            "job_type": "phase1_analysis",
                        }
                    ),
                    202,
                )

            # Sync path — download + run service
            try:
                raw_bytes = storage_backend.download(uf.path)
            except Exception:
                return jsonify({"error": "storage_unavailable", "message": "Could not read the document"}), 502

            ext = os.path.splitext(uf.name.lower())[1]
            fd, tmp_path = tempfile.mkstemp(suffix=ext)
            try:
                with os.fdopen(fd, "wb") as tmp_f:
                    tmp_f.write(raw_bytes)
                existing = load_analysis_result(db, AnalysisPipelineResult, doc_id)
                if existing and existing.status.value == "done" and not force:
                    if existing.content_hash and uf.content_hash and existing.content_hash == uf.content_hash:
                        return jsonify({"status": "cached", **existing.to_api_dict()}), 200

                result = AnalysisPipelineService().analyze_file_path(
                    tmp_path,
                    file_id=doc_id,
                    options=AnalysisOptions(force=force),
                )
                from .persistence import apply_metadata_to_user_file, save_analysis_result

                save_analysis_result(db, AnalysisPipelineResult, result, user_id=user_id)
                fields = extract_bibliographic_fields(result.phase_results)
                apply_metadata_to_user_file(uf, fields, only_empty=True)
                if result.content_hash and not uf.content_hash:
                    uf.content_hash = result.content_hash
                db.commit()
                return jsonify(result.to_api_dict()), 200 if result.status.value != "failed" else 500
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
        finally:
            db.close()

    @bp.route("/<int:doc_id>/pipeline", methods=["GET"])
    @jwt_required()
    def get_pipeline(doc_id: int):
        user_id = int(g.current_user)
        db = SessionLocal()
        try:
            uf = db.get(UserFile, doc_id)
            if not uf or uf.user_id != user_id:
                return jsonify({"error": "not_found", "message": "Document not found"}), 404
            result = load_analysis_result(db, AnalysisPipelineResult, doc_id)
            if result is None:
                return (
                    jsonify(
                        {
                            "error": "not_found",
                            "message": "No Phase 1 analysis yet. POST /api/documents/{id}/analyze",
                        }
                    ),
                    404,
                )
            include_context = request.args.get("include_prompt_context") == "1"
            payload = result.to_api_dict()
            if include_context:
                payload["prompt_context"] = build_phase1_prompt_context(result.phase_results)
            return jsonify(payload), 200
        finally:
            db.close()

    @bp.route("/<int:doc_id>/phases/<phase>", methods=["GET"])
    @jwt_required()
    def get_phase(doc_id: int, phase: str):
        if phase not in _VALID_PHASES:
            return (
                jsonify({"error": "invalid_phase", "message": f"Valid phases: {sorted(_VALID_PHASES)}"}),
                400,
            )
        user_id = int(g.current_user)
        db = SessionLocal()
        try:
            uf = db.get(UserFile, doc_id)
            if not uf or uf.user_id != user_id:
                return jsonify({"error": "not_found", "message": "Document not found"}), 404
            result = load_analysis_result(db, AnalysisPipelineResult, doc_id)
            if result is None or phase not in result.phase_results:
                return jsonify({"error": "not_found", "message": f"Phase {phase!r} not available"}), 404
            return jsonify({"document_id": doc_id, "phase": phase, "result": result.phase_results[phase]}), 200
        finally:
            db.close()

    return bp
