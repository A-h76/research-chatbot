"""Multi-paper compare + gap-finder routes extracted from server.py (Phase 3).

Owns /api/analysis/compare* and /api/analysis/gaps* only.
Single-paper analysis pipeline remains in analysis_pipeline/routes.py.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading

from flask import Blueprint, jsonify, request, session


_COMPARE_PROMPT = """You are an expert research analyst comparing multiple academic papers.

Given the structured analyses of {n} papers below, produce a JSON object with the following keys. Use null for any section that genuinely cannot be answered from the provided analyses. Never fabricate. Be specific.

Keys:
  overview         – 2-3 sentence description of what these papers share and how they differ
  similarities     – array of strings: themes, approaches, or findings common to ALL papers
  differences      – array of strings: key ways the papers diverge (method, scope, results)
  common_datasets  – array of dataset names used by 2 or more papers ([] if none)
  methodologies    – object {{paper_title: one-line methodology summary}} for each paper
  agreements       – array: claims or conclusions the papers agree on
  contradictions   – array: claims or findings that conflict across papers
  research_trends  – array: patterns or directions evident across the set
  synthesis        – 3-5 sentences: what does reading these papers together reveal?

Papers (as structured analyses):
{analyses}
"""

_COMPARE_MAX_ANALYSES_CHARS = 20_000

_GAP_PROMPT = """You are an expert research analyst identifying gaps, open questions, and opportunities across a set of academic papers.

Given the structured analyses of {n} papers, produce a JSON object with the keys below. Base every finding strictly on the provided content — never fabricate gaps, assumptions, or ideas. If you are uncertain, say so rather than inventing something.

IMPORTANT: Label all output explicitly as AI-generated suggestions, not factual claims. This is enforced in the output keys themselves.

Keys:
  preamble              – 1-2 sentences: what field / subfield these papers cover
  underexplored_topics  – array of strings: topics the papers acknowledge but do not thoroughly investigate
  missing_experiments   – array of strings: experiments that would strengthen claims but are absent from these papers
  open_questions        – array of strings: explicit research questions raised but not resolved across the set
  methodological_gaps   – array of strings: limitations in methods used that future work should address
  dataset_gaps          – array of strings: missing data, domains, or populations not studied
  potential_thesis_ideas– array of strings: concrete thesis/dissertation topics a researcher could pursue based on these gaps
  future_opportunities  – array of strings: promising research directions emerging from the combined findings
  disclaimer            – MUST equal exactly: "These are AI-generated suggestions based on the provided paper analyses. They should be treated as starting points for your own critical assessment, not as definitive research conclusions."

Papers (as structured analyses):
{analyses}
"""

_GAP_MAX_ANALYSES_CHARS = 20_000

_GAP_DISCLAIMER = (
    "These are AI-generated suggestions based on the provided paper "
    "analyses. They should be treated as starting points for your own "
    "critical assessment, not as definitive research conclusions."
)


def _selection_hash(file_ids: list[int]) -> str:
    key = ",".join(str(i) for i in sorted(set(file_ids)))
    return hashlib.sha256(key.encode()).hexdigest()


def _derived_to_dict(da) -> dict:
    data = {}
    if da.data:
        try:
            data = json.loads(da.data)
        except Exception:
            pass
    return {
        "id": da.id,
        "kind": da.kind,
        "file_ids": json.loads(da.file_ids) if da.file_ids else [],
        "status": "done" if data else "pending",
        "data": data,
        "model": da.model or "",
        "created_at": da.created_at.isoformat() if da.created_at else None,
    }


def create_derived_analysis_blueprint(
    *,
    SessionLocal,
    UserFile,
    PaperAnalysis,
    DerivedAnalysis,
    select_fn,
    login_required,
    limiter,
    ai_gateway,
    get_model_registry,
    utility_model,
):
    bp = Blueprint("derived_analysis_routes", __name__)
    log = logging.getLogger(__name__)

    def _invoke_json_llm(
        prompt: str,
        *,
        user_id: int,
        path: str,
        task: str,
        resolve_fn,
        prompt_version: str,
    ) -> str:
        from backend.ai.utility_engine import invoke_prompt_llm

        db = SessionLocal()
        try:
            registry = get_model_registry(db)
            plan = resolve_fn()
            content, _ = invoke_prompt_llm(
                ai_gateway=ai_gateway,
                model_registry=registry,
                prompt=prompt,
                plan=plan,
                prompt_version=prompt_version,
                path=path,
                task=task,
                user_id=user_id,
                json_mode=True,
            )
            return content
        finally:
            db.close()

    def _run_comparison(derived_id: int, analyses_payload: str, file_ids: list[int]) -> None:
        db = SessionLocal()
        try:
            da = db.get(DerivedAnalysis, derived_id)
            if not da:
                return

            prompt = _COMPARE_PROMPT.format(
                n=len(file_ids),
                analyses=analyses_payload[:_COMPARE_MAX_ANALYSES_CHARS],
            )
            from backend.ai.capability_router.utility_resolve import (
                PROMPT_VERSION_COMPARE,
                resolve_compare_execution,
            )

            raw = _invoke_json_llm(
                prompt,
                user_id=da.user_id,
                path="compare_papers",
                task="compare",
                resolve_fn=resolve_compare_execution,
                prompt_version=PROMPT_VERSION_COMPARE,
            )
            data = json.loads(raw)

            for arr_key in (
                "similarities",
                "differences",
                "common_datasets",
                "agreements",
                "contradictions",
                "research_trends",
            ):
                v = data.get(arr_key)
                if not isinstance(v, list):
                    data[arr_key] = [v] if v and isinstance(v, str) else []
            if not isinstance(data.get("methodologies"), dict):
                data["methodologies"] = {}

            da = db.get(DerivedAnalysis, derived_id)
            if not da:
                return
            da.data = json.dumps(data, ensure_ascii=False)
            da.model = utility_model
            db.commit()

        except Exception as exc:
            log.warning("comparison failed for derived_id=%s: %s", derived_id, exc)
            try:
                da2 = db.get(DerivedAnalysis, derived_id)
                if da2:
                    da2.data = json.dumps({"error": str(exc)})
                    da2.model = ""
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

    def _run_gap_finder(derived_id: int, analyses_payload: str, file_ids: list[int]) -> None:
        db = SessionLocal()
        try:
            da = db.get(DerivedAnalysis, derived_id)
            if not da:
                return

            prompt = _GAP_PROMPT.format(
                n=len(file_ids),
                analyses=analyses_payload[:_GAP_MAX_ANALYSES_CHARS],
            )
            from backend.ai.capability_router.utility_resolve import (
                PROMPT_VERSION_GAPS,
                resolve_gaps_execution,
            )

            raw = _invoke_json_llm(
                prompt,
                user_id=da.user_id,
                path="gap_finder",
                task="literature_review",
                resolve_fn=resolve_gaps_execution,
                prompt_version=PROMPT_VERSION_GAPS,
            )
            data = json.loads(raw)

            data["disclaimer"] = _GAP_DISCLAIMER

            for arr_key in (
                "underexplored_topics",
                "missing_experiments",
                "open_questions",
                "methodological_gaps",
                "dataset_gaps",
                "potential_thesis_ideas",
                "future_opportunities",
            ):
                v = data.get(arr_key)
                if not isinstance(v, list):
                    data[arr_key] = [v] if v and isinstance(v, str) else []

            da = db.get(DerivedAnalysis, derived_id)
            if not da:
                return
            da.data = json.dumps(data, ensure_ascii=False)
            da.model = utility_model
            db.commit()

        except Exception as exc:
            log.warning("gap finder failed for derived_id=%s: %s", derived_id, exc)
            try:
                da2 = db.get(DerivedAnalysis, derived_id)
                if da2:
                    da2.data = json.dumps({"error": str(exc)})
                    da2.model = ""
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

    def _collect_ready_papers(db, uid, file_ids):
        valid_ids = []
        skipped = []
        paper_blobs = {}

        for fid in file_ids:
            uf = db.get(UserFile, fid)
            if not uf or uf.user_id != uid:
                skipped.append({"id": fid, "reason": "not_found"})
                continue
            pa = db.execute(select_fn(PaperAnalysis).where(PaperAnalysis.file_id == fid)).scalar_one_or_none()
            if not pa or pa.status != "done":
                skipped.append(
                    {
                        "id": fid,
                        "name": uf.title or uf.name,
                        "reason": "analysis_not_ready",
                    }
                )
                continue
            valid_ids.append(fid)
            paper_blobs[fid] = {
                "title": uf.title or uf.name,
                "authors": uf.authors or "",
                "year": uf.year or "",
                "analysis": json.loads(pa.data) if pa.data else {},
            }
        return valid_ids, skipped, paper_blobs

    @bp.route("/api/analysis/compare", methods=["POST"])
    @login_required
    @limiter.limit("20 per hour")
    def compare_papers():
        data = request.get_json(silent=True) or {}
        uid = session["user_id"]
        file_ids = [int(i) for i in (data.get("file_ids") or []) if i]
        project_id = data.get("project_id")
        force = bool(data.get("force"))

        if len(file_ids) < 2:
            return (
                jsonify({"error": "too_few", "detail": "Select at least 2 papers to compare."}),
                400,
            )
        if len(file_ids) > 10:
            return (
                jsonify({"error": "too_many", "detail": "Maximum 10 papers per comparison."}),
                400,
            )

        db = SessionLocal()
        try:
            valid_ids, skipped, paper_blobs = _collect_ready_papers(db, uid, file_ids)

            if len(valid_ids) < 2:
                return (
                    jsonify(
                        {
                            "error": "too_few_ready",
                            "detail": "At least 2 papers need a completed analysis. "
                            "Try again after analysis finishes.",
                            "skipped": skipped,
                        }
                    ),
                    400,
                )

            sel_hash = _selection_hash(valid_ids)

            existing = db.execute(
                select_fn(DerivedAnalysis).where(
                    DerivedAnalysis.user_id == uid,
                    DerivedAnalysis.kind == "compare",
                    DerivedAnalysis.selection_hash == sel_hash,
                )
            ).scalar_one_or_none()

            if existing and not force:
                result = _derived_to_dict(existing)
                result["skipped"] = skipped
                return jsonify(result)

            blobs_text = json.dumps([paper_blobs[fid] for fid in valid_ids], ensure_ascii=False, indent=1)

            if existing:
                existing.data = ""
                existing.model = ""
                existing.file_ids = json.dumps(valid_ids)
                db.commit()
                da_id = existing.id
            else:
                da = DerivedAnalysis(
                    user_id=uid,
                    project_id=project_id,
                    kind="compare",
                    selection_hash=sel_hash,
                    file_ids=json.dumps(valid_ids),
                )
                db.add(da)
                db.commit()
                da_id = da.id

            threading.Thread(
                target=_run_comparison,
                args=(da_id, blobs_text, valid_ids),
                daemon=True,
            ).start()

            return jsonify(
                {
                    "id": da_id,
                    "kind": "compare",
                    "status": "running",
                    "file_ids": valid_ids,
                    "skipped": skipped,
                    "data": {},
                }
            )
        finally:
            db.close()

    @bp.route("/api/analysis/compare/<int:da_id>", methods=["GET"])
    @login_required
    def get_comparison(da_id):
        db = SessionLocal()
        try:
            da = db.get(DerivedAnalysis, da_id)
            if not da or da.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            return jsonify(_derived_to_dict(da))
        finally:
            db.close()

    @bp.route("/api/analysis/compare/<int:da_id>", methods=["DELETE"])
    @login_required
    def delete_comparison(da_id):
        db = SessionLocal()
        try:
            da = db.get(DerivedAnalysis, da_id)
            if not da or da.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            db.delete(da)
            db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    @bp.route("/api/analysis/gaps", methods=["POST"])
    @login_required
    @limiter.limit("20 per hour")
    def find_gaps():
        data = request.get_json(silent=True) or {}
        uid = session["user_id"]
        file_ids = [int(i) for i in (data.get("file_ids") or []) if i]
        project_id = data.get("project_id")
        force = bool(data.get("force"))

        if len(file_ids) < 2:
            return jsonify({"error": "too_few", "detail": "Select at least 2 papers."}), 400
        if len(file_ids) > 10:
            return (
                jsonify({"error": "too_many", "detail": "Maximum 10 papers per gap analysis."}),
                400,
            )

        db = SessionLocal()
        try:
            valid_ids, skipped, paper_blobs = _collect_ready_papers(db, uid, file_ids)

            if len(valid_ids) < 2:
                return (
                    jsonify(
                        {
                            "error": "too_few_ready",
                            "detail": "At least 2 papers need a completed analysis.",
                            "skipped": skipped,
                        }
                    ),
                    400,
                )

            sel_hash = _selection_hash(valid_ids)

            existing = db.execute(
                select_fn(DerivedAnalysis).where(
                    DerivedAnalysis.user_id == uid,
                    DerivedAnalysis.kind == "gaps",
                    DerivedAnalysis.selection_hash == sel_hash,
                )
            ).scalar_one_or_none()

            if existing and not force:
                result = _derived_to_dict(existing)
                result["skipped"] = skipped
                return jsonify(result)

            blobs_text = json.dumps([paper_blobs[fid] for fid in valid_ids], ensure_ascii=False, indent=1)

            if existing:
                existing.data = ""
                existing.model = ""
                existing.file_ids = json.dumps(valid_ids)
                db.commit()
                da_id = existing.id
            else:
                da = DerivedAnalysis(
                    user_id=uid,
                    project_id=project_id,
                    kind="gaps",
                    selection_hash=sel_hash,
                    file_ids=json.dumps(valid_ids),
                )
                db.add(da)
                db.commit()
                da_id = da.id

            threading.Thread(
                target=_run_gap_finder,
                args=(da_id, blobs_text, valid_ids),
                daemon=True,
            ).start()

            return jsonify(
                {
                    "id": da_id,
                    "kind": "gaps",
                    "status": "running",
                    "file_ids": valid_ids,
                    "skipped": skipped,
                    "data": {},
                }
            )
        finally:
            db.close()

    @bp.route("/api/analysis/gaps/<int:da_id>", methods=["GET"])
    @login_required
    def get_gaps(da_id):
        db = SessionLocal()
        try:
            da = db.get(DerivedAnalysis, da_id)
            if not da or da.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            return jsonify(_derived_to_dict(da))
        finally:
            db.close()

    @bp.route("/api/analysis/gaps/<int:da_id>", methods=["DELETE"])
    @login_required
    def delete_gaps(da_id):
        db = SessionLocal()
        try:
            da = db.get(DerivedAnalysis, da_id)
            if not da or da.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            db.delete(da)
            db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    return bp
