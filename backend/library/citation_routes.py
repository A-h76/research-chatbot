"""Citation manager routes extracted from server.py (A-304 Metadata).

Behavior is intentionally preserved; this module only moves route boundaries.
"""

from __future__ import annotations

import io

from flask import Blueprint, jsonify, request, send_file, session


def bibtex_entry(c):
    first_author = (c.authors or "anon").split(";")[0].split(",")[0].strip()
    key = "".join(ch for ch in first_author if ch.isalnum()).lower() + (c.year or "")
    fields = []
    if c.authors:
        fields.append(f"  author = {{{c.authors}}}")
    if c.title:
        fields.append(f"  title = {{{c.title}}}")
    if c.venue:
        fields.append(f"  journal = {{{c.venue}}}")
    if c.year:
        fields.append(f"  year = {{{c.year}}}")
    if c.doi:
        fields.append(f"  doi = {{{c.doi}}}")
    if c.url:
        fields.append(f"  url = {{{c.url}}}")
    return "@article{" + (key or "ref") + ",\n" + ",\n".join(fields) + "\n}"


def apa_entry(c) -> str:
    raw_authors = [a.strip() for a in (c.authors or "").split(";") if a.strip()]
    if not raw_authors:
        author_str = "Unknown Author"
    elif len(raw_authors) == 1:
        author_str = raw_authors[0]
    elif len(raw_authors) <= 20:
        author_str = ", ".join(raw_authors[:-1]) + ", & " + raw_authors[-1]
    else:
        author_str = ", ".join(raw_authors[:19]) + ", ... " + raw_authors[-1]

    year_part = f"({c.year}). " if c.year else ""
    title_part = f"{c.title}. " if c.title else ""
    venue_part = f"*{c.venue}*. " if c.venue else ""
    doi_part = f"https://doi.org/{c.doi}" if c.doi else (c.url or "")

    return f"{author_str}. {year_part}{title_part}{venue_part}{doi_part}".strip().rstrip(".")


def ieee_entry(c) -> str:
    raw_authors = [a.strip() for a in (c.authors or "").split(";") if a.strip()]

    def _to_ieee_name(author: str) -> str:
        parts = [p.strip() for p in author.split(",", 1)]
        if len(parts) == 2:
            last, first = parts
            initials = ". ".join(w[0] for w in first.split() if w) + "."
            return f"{initials} {last}"
        return author

    if not raw_authors:
        author_str = "Unknown"
    elif len(raw_authors) == 1:
        author_str = _to_ieee_name(raw_authors[0])
    elif len(raw_authors) <= 3:
        names = [_to_ieee_name(a) for a in raw_authors]
        author_str = " and ".join(names)
    else:
        author_str = _to_ieee_name(raw_authors[0]) + " et al."

    title_part = f'"{c.title}," ' if c.title else ""
    venue_part = f"*{c.venue}*, " if c.venue else ""
    year_part = f"{c.year}. " if c.year else ""
    doi_part = f"doi: {c.doi}" if c.doi else (c.url or "")

    return f"{author_str}, {title_part}{venue_part}{year_part}{doi_part}".strip()


def format_citation(c, fmt: str = "bibtex") -> str:
    if fmt == "apa":
        return apa_entry(c)
    if fmt == "ieee":
        return ieee_entry(c)
    return bibtex_entry(c)


def _citation_to_dict(c, fmt: str = "bibtex") -> dict:
    return {
        "id": c.id,
        "authors": c.authors or "",
        "title": c.title or "",
        "year": c.year or "",
        "venue": c.venue or "",
        "doi": c.doi or "",
        "url": c.url or "",
        "notes": c.notes or "",
        "project_id": c.project_id,
        "bibtex": bibtex_entry(c),
        "apa": apa_entry(c),
        "ieee": ieee_entry(c),
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def create_citation_blueprint(
    *,
    SessionLocal,
    Citation,
    Project,
    UserFile,
    select_fn,
    login_required,
    resolve_owned_project_id,
    log_security_event,
    app_logger,
):
    bp = Blueprint("citation_routes", __name__)

    @bp.route("/api/citations", methods=["GET"])
    @login_required
    def list_citations():
        uid = session["user_id"]
        args = request.args
        project_id_raw = args.get("project_id")
        q = args.get("q", "").strip().lower() or None

        db = SessionLocal()
        try:
            stmt = select_fn(Citation).where(Citation.user_id == uid)
            if project_id_raw is not None:
                try:
                    pid = int(project_id_raw)
                    stmt = stmt.where(Citation.project_id == pid if pid else Citation.project_id.is_(None))
                except (TypeError, ValueError):
                    pass
            cits = db.execute(stmt.order_by(Citation.created_at.desc())).scalars().all()
            if q:
                cits = [
                    c
                    for c in cits
                    if q in (c.title or "").lower()
                    or q in (c.authors or "").lower()
                    or q in (c.venue or "").lower()
                ]
            return jsonify([_citation_to_dict(c) for c in cits])
        finally:
            db.close()

    @bp.route("/api/citations", methods=["POST"])
    @login_required
    def create_citation():
        d = request.get_json(silent=True) or {}
        uid = session["user_id"]
        db = SessionLocal()
        try:
            project_id = d.get("project_id")
            if project_id:
                project_id, denied = resolve_owned_project_id(db, Project, project_id, uid)
                if denied:
                    log_security_event(
                        "authz_denied",
                        resource="project",
                        action="create_citation",
                        user_id=uid,
                        project_id=d.get("project_id"),
                    )
            c = Citation(
                user_id=uid,
                project_id=project_id,
                authors=str(d.get("authors", ""))[:500],
                title=str(d.get("title", ""))[:500],
                year=str(d.get("year", ""))[:10],
                venue=str(d.get("venue", ""))[:300],
                doi=str(d.get("doi", ""))[:200],
                url=str(d.get("url", ""))[:600],
                notes=str(d.get("notes", ""))[:2000],
            )
            db.add(c)
            db.commit()
            return jsonify(_citation_to_dict(c)), 201
        finally:
            db.close()

    @bp.route("/api/citations/<int:cid>", methods=["GET"])
    @login_required
    def get_citation(cid):
        db = SessionLocal()
        try:
            c = db.get(Citation, cid)
            if not c or c.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            return jsonify(_citation_to_dict(c))
        finally:
            db.close()

    @bp.route("/api/citations/<int:cid>/format", methods=["GET"])
    @login_required
    def scholarly_format_citation(cid):
        from backend.scholarly.crossref import format_citation as crossref_format

        style = (request.args.get("style") or "apa").lower()
        if style not in ("apa", "ieee", "bibtex", "mla"):
            return jsonify({"error": "unsupported style"}), 400

        db = SessionLocal()
        try:
            c = db.get(Citation, cid)
            if not c or c.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404

            local = format_citation(c, style if style != "mla" else "apa")
            doi = (c.doi or "").strip()
            if not doi:
                return jsonify(
                    {
                        "citation": local,
                        "source": "ai",
                        "verified": False,
                        "message": "No DOI — showing locally formatted citation.",
                    }
                )

            try:
                result = crossref_format(doi, style, db)
            except Exception as exc:
                app_logger.warning("citation format Crossref failed cid=%s: %s", cid, exc)
                result = None

            if result and result.get("verified") and result.get("citation"):
                return jsonify(result)

            return jsonify(
                {
                    "citation": local or (result or {}).get("citation") or "",
                    "source": "ai",
                    "verified": False,
                    "message": "Crossref unavailable — showing locally formatted citation.",
                }
            )
        finally:
            db.close()

    @bp.route("/api/citations/<int:cid>", methods=["PATCH"])
    @login_required
    def update_citation(cid):
        d = request.get_json(silent=True) or {}
        uid = session["user_id"]
        db = SessionLocal()
        try:
            c = db.get(Citation, cid)
            if not c or c.user_id != uid:
                return jsonify({"error": "not_found"}), 404
            for field, maxlen in (
                ("authors", 500),
                ("title", 500),
                ("year", 10),
                ("venue", 300),
                ("doi", 200),
                ("url", 600),
                ("notes", 2000),
            ):
                if field in d:
                    setattr(c, field, str(d[field] or "")[:maxlen])
            if "project_id" in d:
                pid = d["project_id"]
                if pid is None:
                    c.project_id = None
                else:
                    p = db.get(Project, pid)
                    if p and p.user_id == uid:
                        c.project_id = pid
            db.commit()
            return jsonify(_citation_to_dict(c))
        finally:
            db.close()

    @bp.route("/api/citations/<int:cid>", methods=["DELETE"])
    @login_required
    def delete_citation(cid):
        db = SessionLocal()
        try:
            c = db.get(Citation, cid)
            if not c or c.user_id != session["user_id"]:
                return jsonify({"error": "not_found"}), 404
            db.delete(c)
            db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    @bp.route("/api/citations/from-paper/<int:fid>", methods=["POST"])
    @login_required
    def citation_from_paper(fid):
        uid = session["user_id"]
        db = SessionLocal()
        try:
            uf = db.get(UserFile, fid)
            if not uf or uf.user_id != uid:
                return jsonify({"error": "not_found"}), 404
            if not uf.title:
                return (
                    jsonify(
                        {
                            "error": "no_metadata",
                            "detail": "This paper has no extracted title yet. "
                            "Wait for metadata extraction to complete.",
                        }
                    ),
                    400,
                )

            existing = db.execute(
                select_fn(Citation).where(
                    Citation.user_id == uid,
                    Citation.title == uf.title,
                )
            ).scalar_one_or_none()
            if existing:
                return jsonify({**_citation_to_dict(existing), "existing": True})

            body = request.get_json(silent=True) or {}
            raw_project_id = body.get("project_id") if "project_id" in body else uf.project_id
            project_id, project_denied = resolve_owned_project_id(db, Project, raw_project_id, uid)
            if project_denied:
                log_security_event(
                    "authz_denied",
                    resource="project",
                    action="citation_from_paper",
                    user_id=uid,
                    project_id=raw_project_id,
                    file_id=fid,
                )

            c = Citation(
                user_id=uid,
                project_id=project_id,
                title=uf.title[:500],
                authors=(uf.authors or "")[:500],
                year=(uf.year or "")[:10],
                venue=(uf.venue or "")[:300],
                doi=(uf.doi or "")[:200],
                url=(f"https://doi.org/{uf.doi}" if uf.doi else "")[:600],
                notes="",
            )
            db.add(c)
            db.commit()
            return jsonify({**_citation_to_dict(c), "existing": False}), 201
        finally:
            db.close()

    @bp.route("/api/citations/export")
    @login_required
    def export_citations():
        uid = session["user_id"]
        fmt = request.args.get("format", "bibtex").lower()
        project_id_raw = request.args.get("project_id")

        db = SessionLocal()
        try:
            stmt = select_fn(Citation).where(Citation.user_id == uid)
            if project_id_raw is not None:
                try:
                    pid = int(project_id_raw)
                    stmt = stmt.where(Citation.project_id == pid if pid else Citation.project_id.is_(None))
                except (TypeError, ValueError):
                    pass
            cits = db.execute(stmt.order_by(Citation.created_at)).scalars().all()

            if fmt in ("apa", "ieee"):
                lines = [format_citation(c, fmt) for c in cits]
                blob = "\n\n".join(lines)
                mime = "text/plain"
                fname = f"references-{fmt}.txt"
            else:
                blob = "\n\n".join(bibtex_entry(c) for c in cits)
                mime = "application/x-bibtex"
                fname = "references.bib"

            return send_file(
                io.BytesIO(blob.encode("utf-8")),
                mimetype=mime,
                as_attachment=True,
                download_name=fname,
            )
        finally:
            db.close()

    return bp
