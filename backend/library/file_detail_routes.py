"""File detail/library routes extracted from server.py monolith.

Behavior is intentionally identical; this module is wiring refactor only.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, redirect, request, session


def create_file_detail_blueprint(
    *,
    SessionLocal,
    UserFile,
    Project,
    PaperAnalysis,
    select_fn,
    login_required,
    limiter,
    storage,
    extract_text,
    sha256_fn,
    enqueue_job,
    adjust_storage_usage,
    file_to_dict,
    analysis_to_dict,
    app_logger,
):
    bp = Blueprint("file_detail", __name__)

    @bp.get("/api/files/<int:fid>")
    @login_required
    def get_file(fid):
        db = SessionLocal()
        try:
            x = db.get(UserFile, fid)
            if not x or x.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            payload = file_to_dict(x)
            if x.project_id:
                p = db.get(Project, x.project_id)
                if p and p.user_id == session["user_id"]:
                    payload["project"] = {"id": p.id, "name": p.name, "emoji": p.emoji or "📁"}
                else:
                    payload["project"] = None
            else:
                payload["project"] = None
            return jsonify(payload)
        finally:
            db.close()

    @bp.patch("/api/files/<int:fid>")
    @login_required
    def patch_file(fid):
        data = request.get_json(silent=True) or {}
        db = SessionLocal()
        try:
            x = db.get(UserFile, fid)
            if not x or x.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404

            # Keep validation/truncation semantics unchanged from server.py.
            import re

            if "title" in data:
                x.title = str(data["title"])[:500]
            if "authors" in data:
                x.authors = str(data["authors"])[:1000]
            if "year" in data:
                y = re.search(r"(19|20)\d{2}", str(data["year"]) or "")
                x.year = y.group(0) if y else ""
            if "venue" in data:
                x.venue = str(data["venue"])[:300]
            if "doi" in data:
                x.doi = str(data["doi"])[:200]
            if "abstract" in data:
                x.abstract = str(data["abstract"])[:8000]
            if "reading_status" in data:
                rs = data["reading_status"]
                if rs in ("unread", "reading", "read"):
                    x.reading_status = rs
            if "tags" in data:
                import json

                tags = [str(t)[:80] for t in (data["tags"] or []) if t][:30]
                x.tags = json.dumps(tags)
            if "project_id" in data:
                from security.authz import resolve_owned_project_id

                raw = data["project_id"]
                if raw in (None, "", "null"):
                    x.project_id = None
                else:
                    pid, denied = resolve_owned_project_id(
                        db, Project, raw, session["user_id"]
                    )
                    if denied:
                        return jsonify({"error": "forbidden", "detail": "project_not_owned"}), 403
                    x.project_id = pid

            db.commit()
            return jsonify(file_to_dict(x))
        finally:
            db.close()

    @bp.get("/api/files/<int:fid>/analysis")
    @login_required
    def get_analysis(fid):
        db = SessionLocal()
        try:
            uf = db.get(UserFile, fid)
            if not uf or uf.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404

            if uf.kind == "image" or uf.text_len == 0:
                return jsonify(
                    {
                        "file_id": fid,
                        "status": "none",
                        "error": "no text content",
                        "model": "",
                        "data": {},
                        "updated_at": None,
                    }
                )

            pa = db.execute(select_fn(PaperAnalysis).where(PaperAnalysis.file_id == fid)).scalar_one_or_none()
            if pa is None:
                h = uf.content_hash or ""
                if not h:
                    with storage.local_copy(uf.path) as local_path:
                        text = extract_text(local_path, uf.mime, uf.name)
                    if text:
                        h = sha256_fn(text)
                        uf.content_hash = h
                enqueue_job(db, uf.user_id, fid, "phase1_analysis")
                db.commit()
                return jsonify(
                    {
                        "file_id": fid,
                        "status": "pending",
                        "error": "",
                        "model": "",
                        "data": {},
                        "updated_at": None,
                    }
                )

            return jsonify(analysis_to_dict(pa))
        finally:
            db.close()

    @bp.post("/api/files/<int:fid>/analysis/refresh")
    @login_required
    def refresh_analysis(fid):
        db = SessionLocal()
        try:
            uf = db.get(UserFile, fid)
            if not uf or uf.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            if uf.kind == "image" or uf.text_len == 0:
                return jsonify({"error": "no_text_content"}), 400

            pa = db.execute(select_fn(PaperAnalysis).where(PaperAnalysis.file_id == fid)).scalar_one_or_none()
            if pa:
                pa.content_hash = ""
                pa.status = "pending"
            else:
                pa = PaperAnalysis(file_id=fid, user_id=uf.user_id, status="pending")
                db.add(pa)

            with storage.local_copy(uf.path) as local_path:
                text = extract_text(local_path, uf.mime, uf.name)
            h = sha256_fn(text) if text else ""
            if h:
                uf.content_hash = h
            enqueue_job(db, uf.user_id, fid, "paper_analysis")
            db.commit()
            return jsonify({"ok": True, "status": "running"})
        finally:
            db.close()

    @bp.get("/api/files/<int:fid>/raw")
    @login_required
    def file_raw(fid):
        db = SessionLocal()
        try:
            x = db.get(UserFile, fid)
            if not x or x.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            if not (x.path or "").strip():
                external = (getattr(x, "source_url", None) or "").strip()
                if not external and (x.doi or "").strip():
                    external = f"https://doi.org/{(x.doi or '').strip()}"
                if external:
                    return redirect(external)
                return (
                    jsonify(
                        {
                            "error": "no_file_bytes",
                            "message": "Metadata-only entry — upload a PDF to open locally.",
                        }
                    ),
                    404,
                )
            url = storage.presigned_url(x.path, x.name, x.mime or "application/octet-stream")
            return redirect(url)
        finally:
            db.close()

    @bp.delete("/api/files/<int:fid>")
    @login_required
    def delete_file(fid):
        db = SessionLocal()
        try:
            x = db.get(UserFile, fid)
            if not x or x.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            if (x.path or "").strip():
                storage.delete(x.path)
            db.delete(x)
            adjust_storage_usage(db, session["user_id"], delta_bytes=-(x.size or 0), delta_files=-1)
            db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    @bp.get("/api/files/<int:fid>/related")
    @login_required
    def scholarly_related(fid):
        from backend.scholarly import provider_enabled
        from backend.scholarly.semantic_scholar import get_related_papers

        if not provider_enabled("semantic_scholar"):
            return (
                jsonify(
                    {
                        "error": "related_disabled",
                        "message": "Related papers are temporarily disabled.",
                        "related": [],
                        "citing": [],
                        "recommended": [],
                    }
                ),
                503,
            )

        db = SessionLocal()
        try:
            uf = db.get(UserFile, fid)
            if not uf or uf.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            bundle = get_related_papers(
                file_id=fid,
                doi=uf.doi or None,
                title=uf.title or uf.name or None,
                db=db,
            )
            if bundle is None:
                return (
                    jsonify(
                        {
                            "error": "related_unavailable",
                            "message": "Recommendations temporarily unavailable.",
                            "related": [],
                            "citing": [],
                            "recommended": [],
                        }
                    ),
                    503,
                )

            def _s2_to_dict(p):
                return {
                    "paper_id": p.paper_id,
                    "doi": p.doi,
                    "title": p.title,
                    "authors": p.authors,
                    "year": p.year,
                    "venue": p.venue,
                    "abstract": p.abstract,
                    "citation_count": p.citation_count,
                    "open_access_url": p.open_access_url,
                    "source": p.source,
                }

            return jsonify(
                {
                    "related": [_s2_to_dict(p) for p in bundle.related],
                    "citing": [_s2_to_dict(p) for p in bundle.citing],
                    "recommended": [_s2_to_dict(p) for p in bundle.recommended],
                    "cached_at": bundle.cached_at,
                    "provider_version": bundle.provider_version,
                }
            )
        except Exception as exc:
            app_logger.warning("scholarly_related fid=%s failed: %s", fid, exc)
            return jsonify({"error": "related_unavailable", "related": [], "citing": [], "recommended": []}), 503
        finally:
            db.close()

    @bp.get("/api/files/<int:fid>/citation")
    @login_required
    def scholarly_citation(fid):
        from backend.scholarly.crossref import format_citation

        style = (request.args.get("style") or "apa").lower()
        if style not in ("apa", "ieee", "bibtex", "mla"):
            return jsonify({"error": "unsupported style"}), 400
        db = SessionLocal()
        try:
            uf = db.get(UserFile, fid)
            if not uf or uf.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            doi = (uf.doi or "").strip()
            if not doi:
                return jsonify(
                    {
                        "citation": "",
                        "source": "ai",
                        "verified": False,
                        "message": "No DOI — use AI-generated citation.",
                    }
                )
            return jsonify(format_citation(doi, style, db))
        except Exception as exc:
            app_logger.warning("scholarly_citation fid=%s failed: %s", fid, exc)
            return jsonify({"citation": "", "source": "ai", "verified": False}), 503
        finally:
            db.close()

    return bp
