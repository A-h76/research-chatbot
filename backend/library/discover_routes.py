"""Discover/OpenAlex routes extracted from server.py monolith.

Behavior is intentionally preserved; this module only moves route boundaries.
"""

from __future__ import annotations

import json

from flask import Blueprint, jsonify, request, session


def create_discover_blueprint(
    *,
    SessionLocal,
    UserFile,
    Project,
    select_fn,
    login_required,
    file_to_dict,
    app_logger,
):
    bp = Blueprint("discover_routes", __name__)

    @bp.route("/api/discover", methods=["GET"])
    @login_required
    def scholarly_discover():
        from backend.scholarly import provider_enabled
        from backend.scholarly.openalex import search_works

        if not provider_enabled("openalex"):
            return (
                jsonify(
                    {
                        "error": "discover_disabled",
                        "message": "OpenAlex Discover is temporarily disabled.",
                        "results": [],
                    }
                ),
                503,
            )

        query = (request.args.get("q") or "").strip()
        if not query:
            return jsonify({"error": "q is required"}), 400
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(20, max(1, int(request.args.get("per_page", 15))))
        db = SessionLocal()
        try:
            works = search_works(query, page=page, per_page=per_page, db=db)
            return jsonify(
                {
                    "results": [
                        {
                            "id": w.id,
                            "doi": w.doi,
                            "title": w.title,
                            "authors": w.authors,
                            "year": w.year,
                            "venue": w.venue,
                            "abstract": w.abstract,
                            "citation_count": w.citation_count,
                            "open_access_url": w.open_access_url,
                            "concepts": w.concepts,
                            "source": w.source,
                        }
                        for w in works
                    ],
                    "page": page,
                    "per_page": per_page,
                }
            )
        except Exception as exc:
            app_logger.warning("scholarly_discover failed: %s", exc)
            return (
                jsonify(
                    {
                        "error": "discover_unavailable",
                        "message": "Discover is temporarily unavailable.",
                        "results": [],
                    }
                ),
                503,
            )
        finally:
            db.close()

    @bp.route("/api/discover/import", methods=["POST"])
    @login_required
    def scholarly_discover_import():
        from backend.scholarly import provider_enabled
        from backend.scholarly.crossref import enrich_file_from_doi

        if not provider_enabled("openalex"):
            return (
                jsonify(
                    {
                        "error": "discover_disabled",
                        "message": "OpenAlex Discover is temporarily disabled.",
                    }
                ),
                503,
            )

        body = request.get_json(silent=True) or {}
        title = (body.get("title") or "").strip()
        doi = (body.get("doi") or "").strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
        authors = (body.get("authors") or "").strip()
        year_raw = body.get("year")
        year = str(year_raw).strip()[:10] if year_raw not in (None, "") else ""
        venue = (body.get("venue") or "").strip()
        abstract = (body.get("abstract") or "").strip()
        open_access_url = (body.get("open_access_url") or "").strip()
        openalex_id = (body.get("openalex_id") or body.get("id") or "").strip()
        project_id = body.get("project_id")
        import_source = (body.get("import_source") or "discover").strip().lower()
        if import_source not in ("discover", "related", "openalex"):
            import_source = "discover"

        if not title and not doi:
            return jsonify({"error": "title_or_doi_required"}), 400

        uid = session["user_id"]
        db = SessionLocal()
        try:
            if project_id is not None:
                try:
                    project_id = int(project_id)
                except (TypeError, ValueError):
                    project_id = None
                if project_id is not None:
                    proj = db.get(Project, project_id)
                    if not proj or proj.user_id != uid:
                        return jsonify({"error": "project_not_found"}), 404

            if doi:
                existing = db.execute(
                    select_fn(UserFile).where(
                        UserFile.user_id == uid,
                        UserFile.doi == doi,
                    )
                ).scalars().first()
                if existing:
                    return jsonify({"already_exists": True, "file": file_to_dict(existing)})

            display_name = (title or f"openalex:{openalex_id}" or "openalex-import")[:300]
            tags = ["from-related"] if import_source == "related" else ["from-discover"]
            if openalex_id:
                if openalex_id.startswith("s2:"):
                    tags.append(openalex_id[:80])
                else:
                    tags.append(f"openalex:{openalex_id[:80]}")

            uf = UserFile(
                user_id=uid,
                project_id=project_id,
                conversation_id=None,
                name=display_name,
                mime="",
                kind="document",
                path="",
                size=0,
                title=(title or display_name)[:500],
                authors=authors[:1000],
                year=year,
                venue=venue[:300],
                doi=doi[:200],
                abstract=abstract[:8000],
                reading_status="unread",
                tags=json.dumps(tags),
                meta_status="done",
                metadata_source="openalex",
                source_url=open_access_url[:500],
                doi_verified=False,
            )
            db.add(uf)
            db.flush()

            if doi:
                try:
                    enrich_file_from_doi(db, uf.id)
                    db.refresh(uf)
                except Exception as cx_exc:
                    app_logger.warning(
                        "discover import crossref enrich skipped file_id=%s: %s", uf.id, cx_exc
                    )

            db.commit()
            return jsonify({"already_exists": False, "file": file_to_dict(uf)}), 201
        except Exception as exc:
            db.rollback()
            app_logger.warning("scholarly_discover_import failed: %s", exc)
            return jsonify({"error": "import_failed"}), 500
        finally:
            db.close()

    return bp
