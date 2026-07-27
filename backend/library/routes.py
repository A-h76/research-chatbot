"""HTTP routes for Library Bridge (factory, no import server)."""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect, request, session

from .bibtex import parse_bibtex, to_bibtex
from .ris import parse_ris, to_ris
from .service import records_from_user_files
from . import zotero as zotero_mod


def create_library_bridge_blueprint(
    *,
    import_service,
    SessionLocal,
    UserFile,
    LibraryConnection,
    Project,
    select_fn,
    login_required,
    app_base_url="",
    enrich_file_from_doi=None,
    limiter=None,
    file_to_dict=None,
    collection_service=None,
):
    bp = Blueprint("library_bridge", __name__)

    def _rate(spec):
        def deco(fn):
            if limiter is None:
                return fn
            return limiter.limit(spec)(fn)

        return deco

    def _uid():
        return session["user_id"]

    def _get_connection(db, user_id: int, provider: str):
        return (
            db.execute(
                select_fn(LibraryConnection).where(
                    LibraryConnection.user_id == user_id,
                    LibraryConnection.provider == provider,
                    LibraryConnection.status == "active",
                )
            )
            .scalars()
            .first()
        )

    def _parse_upload_text() -> tuple[str, str]:
        """Return (format, text) from multipart file or JSON body."""
        fmt = (request.args.get("format") or request.form.get("format") or "").lower()
        if "file" in request.files and request.files["file"].filename:
            f = request.files["file"]
            raw = f.read()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
            name = (f.filename or "").lower()
            if not fmt:
                if name.endswith(".ris"):
                    fmt = "ris"
                else:
                    fmt = "bibtex"
            return fmt, text
        data = request.get_json(silent=True) or {}
        text = data.get("content") or data.get("text") or ""
        fmt = (fmt or data.get("format") or "bibtex").lower()
        return fmt, text

    # ── Status / Connect cards ──────────────────────────────────────────
    @bp.route("/api/library/connections", methods=["GET"])
    @login_required
    def list_connections():
        db = SessionLocal()
        try:
            rows = (
                db.execute(
                    select_fn(LibraryConnection).where(
                        LibraryConnection.user_id == _uid(),
                        LibraryConnection.status == "active",
                    )
                )
                .scalars()
                .all()
            )
            connected = {r.provider: r for r in rows}
            z = connected.get("zotero")
            m = connected.get("mendeley")
            z_meta = {}
            if z and z.meta_json:
                try:
                    z_meta = json.loads(z.meta_json)
                except Exception:
                    z_meta = {}
            return jsonify(
                {
                    "zotero": {
                        "available": zotero_mod.zotero_configured(),
                        "connected": bool(z),
                        "username": z_meta.get("username") or "",
                        "external_user_id": (z.external_user_id if z else "") or "",
                    },
                    "mendeley": {
                        "available": False,
                        "connected": bool(m),
                        "coming_soon": True,
                        "username": "",
                    },
                    "formats": ["bibtex", "ris"],
                }
            )
        finally:
            db.close()

    # ── BibTeX / RIS import ─────────────────────────────────────────────
    @bp.route("/api/library/import", methods=["POST"])
    @login_required
    @_rate("10 per hour")
    def import_library():
        fmt, text = _parse_upload_text()
        if not text.strip():
            return jsonify({"error": "empty_content"}), 400
        if fmt in {"bib", "bibtex", "biblatex"}:
            records = parse_bibtex(text)
            source_tag = "from-bibtex"
        elif fmt == "ris":
            records = parse_ris(text)
            source_tag = "from-ris"
        else:
            return jsonify({"error": "unsupported_format", "detail": "Use bibtex or ris."}), 400

        if not records:
            return jsonify({"error": "no_records", "detail": "No bibliographic entries found."}), 400

        body = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
        # form + JSON hybrid: JSON body may accompany multipart
        if request.files and request.is_json is False:
            raw_json = request.form.get("json")
            if raw_json:
                try:
                    body = {**body, **json.loads(raw_json)}
                except Exception:
                    pass
        create_project = str(body.get("create_project") or "").lower() in {"1", "true", "yes"}
        project_name = (body.get("project_name") or body.get("create_project_name") or "").strip() or None
        if create_project and not project_name:
            project_name = f"Import {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        if not create_project:
            project_name = None

        try:
            pid = int(body.get("project_id")) if body.get("project_id") not in (None, "", "null") else None
        except (TypeError, ValueError):
            pid = None

        create_collection = str(body.get("create_collection") or "").lower() in {"1", "true", "yes"}
        collection_name = (body.get("collection_name") or "").strip() or None
        if create_collection and not collection_name:
            collection_name = f"Import {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        if not create_collection:
            collection_name = None
        try:
            cid = int(body.get("collection_id")) if body.get("collection_id") not in (None, "", "null") else None
        except (TypeError, ValueError):
            cid = None

        result = import_service.import_records(
            _uid(),
            records,
            project_id=None if project_name else pid,
            create_project_name=project_name,
            collection_id=cid,
            create_collection_name=collection_name,
            source_tag=source_tag,
        )
        if result.get("error"):
            status = 404 if result["error"] == "project_not_found" else 400
            if result["error"] == "import_failed":
                status = 500
            return jsonify(result), status
        return jsonify({**result, "format": fmt, "parsed": len(records)}), 201

    # ── Export library files as BibTeX / RIS ────────────────────────────
    @bp.route("/api/library/export", methods=["GET"])
    @login_required
    def export_library():
        from flask import send_file

        fmt = (request.args.get("format") or "bibtex").lower()
        project_id_raw = request.args.get("project_id")
        uid = _uid()
        db = SessionLocal()
        try:
            stmt = select_fn(UserFile).where(
                UserFile.user_id == uid,
                UserFile.kind == "document",
            )
            if project_id_raw not in (None, ""):
                try:
                    pid = int(project_id_raw)
                    stmt = stmt.where(UserFile.project_id == pid)
                except (TypeError, ValueError):
                    pass
            files = db.execute(stmt.order_by(UserFile.created_at.desc()).limit(2000)).scalars().all()
            records = records_from_user_files(files)
            if fmt == "ris":
                blob = to_ris(records)
                mime = "application/x-research-info-systems"
                fname = "library.ris"
            else:
                blob = to_bibtex(records)
                mime = "application/x-bibtex"
                fname = "library.bib"
            return send_file(
                io.BytesIO(blob.encode("utf-8")),
                mimetype=mime,
                as_attachment=True,
                download_name=fname,
            )
        finally:
            db.close()

    # ── Zotero OAuth + import ───────────────────────────────────────────
    @bp.route("/api/library/zotero/connect", methods=["GET", "POST"])
    @login_required
    @_rate("20 per hour")
    def zotero_connect():
        if not zotero_mod.zotero_configured():
            return jsonify(
                {
                    "error": "zotero_not_configured",
                    "detail": "Set ZOTERO_CLIENT_KEY and ZOTERO_CLIENT_SECRET.",
                    "coming_soon": False,
                }
            ), 503
        callback = f"{app_base_url.rstrip('/')}/api/library/zotero/callback"
        try:
            started = zotero_mod.begin_oauth(callback)
        except Exception as exc:
            return jsonify({"error": "oauth_start_failed", "detail": str(exc)[:200]}), 502
        session["zotero_oauth"] = {
            "request_token": started["request_token"],
            "request_token_secret": started["request_token_secret"],
        }
        if request.method == "GET" and request.args.get("redirect") == "1":
            return redirect(started["authorize_url"])
        return jsonify({"authorize_url": started["authorize_url"]})

    @bp.route("/api/library/zotero/callback", methods=["GET"])
    @login_required
    def zotero_callback():
        if not zotero_mod.zotero_configured():
            return redirect("/library?zotero=not_configured")
        pending = session.pop("zotero_oauth", None) or {}
        args = zotero_mod.parse_oauth_callback_args(request.args)
        if not pending.get("request_token") or not args.get("oauth_verifier"):
            return redirect("/library?zotero=denied")
        callback = f"{app_base_url.rstrip('/')}/api/library/zotero/callback"
        try:
            tokens = zotero_mod.finish_oauth(
                request_token=pending["request_token"],
                request_token_secret=pending["request_token_secret"],
                oauth_verifier=args["oauth_verifier"],
                callback_uri=callback,
            )
        except Exception:
            return redirect("/library?zotero=error")

        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "zotero")
            meta = json.dumps({"username": tokens.get("username") or ""})
            if not row:
                row = LibraryConnection(
                    user_id=_uid(),
                    provider="zotero",
                    external_user_id=tokens.get("user_id") or "",
                    access_token=tokens.get("access_token") or "",
                    access_secret=tokens.get("access_secret") or "",
                    meta_json=meta,
                    status="active",
                )
                db.add(row)
            else:
                row.external_user_id = tokens.get("user_id") or row.external_user_id
                row.access_token = tokens.get("access_token") or ""
                row.access_secret = tokens.get("access_secret") or ""
                row.meta_json = meta
                row.status = "active"
                row.updated_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()
        return redirect("/library?zotero=connected")

    @bp.route("/api/library/zotero/disconnect", methods=["POST"])
    @login_required
    def zotero_disconnect():
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "zotero")
            if row:
                row.status = "revoked"
                row.access_token = ""
                row.access_secret = ""
                row.updated_at = datetime.now(timezone.utc)
                db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    @bp.route("/api/library/zotero/collections", methods=["GET"])
    @login_required
    def zotero_collections():
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "zotero")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            try:
                items = zotero_mod.list_collections(
                    row.access_token, row.access_secret, row.external_user_id
                )
            except Exception as exc:
                return jsonify({"error": "zotero_api_error", "detail": str(exc)[:200]}), 502
            return jsonify({"items": items})
        finally:
            db.close()

    @bp.route("/api/library/zotero/import", methods=["POST"])
    @login_required
    @_rate("5 per hour")
    def zotero_import():
        data = request.get_json(silent=True) or {}
        collection_key = (data.get("collection_key") or "all").strip()
        coll_name = ""
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "zotero")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            try:
                if collection_key not in {"all", "", "root"}:
                    z_cols = zotero_mod.list_collections(
                        row.access_token, row.access_secret, row.external_user_id
                    )
                    for c in z_cols:
                        if c.get("key") == collection_key:
                            coll_name = c.get("name") or ""
                            break
                records = zotero_mod.fetch_items(
                    row.access_token,
                    row.access_secret,
                    row.external_user_id,
                    collection_key=collection_key,
                    collection_name=coll_name,
                    limit=int(data.get("limit") or 200),
                )
            except Exception as exc:
                return jsonify({"error": "zotero_api_error", "detail": str(exc)[:200]}), 502
        finally:
            db.close()

        if not records:
            return jsonify({"error": "no_records", "detail": "No items in that collection."}), 400

        project_name = data.get("project_name")
        create_project = data.get("create_project")
        if create_project in (True, "1", "true", "yes") and not project_name:
            project_name = f"Zotero {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        if create_project not in (True, "1", "true", "yes"):
            project_name = project_name if data.get("project_name") else None

        try:
            pid = int(data["project_id"]) if data.get("project_id") not in (None, "") else None
        except (TypeError, ValueError):
            pid = None

        result = import_service.import_records(
            _uid(),
            records,
            project_id=pid if not project_name else None,
            create_project_name=project_name,
            source_tag="from-zotero",
        )
        if result.get("error"):
            status = 404 if result["error"] == "project_not_found" else 500
            return jsonify(result), status
        return jsonify({**result, "parsed": len(records), "source": "zotero"}), 201

    @bp.route("/api/library/mendeley/connect", methods=["GET", "POST"])
    @login_required
    def mendeley_connect():
        return jsonify(
            {
                "error": "coming_soon",
                "detail": "Mendeley one-click import is next. Export RIS/BibTeX from Mendeley today.",
                "coming_soon": True,
                "fallback": ["bibtex", "ris"],
            }
        ), 503

    @bp.route("/api/library/facets", methods=["GET"])
    @login_required
    def library_facets():
        from backend.library.search import facets_for_user

        uid = session["user_id"]
        project_id_raw = request.args.get("project_id")
        project_id = None
        if project_id_raw not in (None, ""):
            try:
                project_id = int(project_id_raw)
            except (TypeError, ValueError):
                project_id = None
        db = SessionLocal()
        try:
            return jsonify(facets_for_user(db, UserFile, uid, project_id=project_id))
        finally:
            db.close()

    # ── Collections (Phase 1.6) ─────────────────────────────────────────
    @bp.route("/api/library/collections", methods=["GET"])
    @login_required
    def list_library_collections():
        if collection_service is None:
            return jsonify({"error": "not_configured"}), 503
        return jsonify({"items": collection_service.list_collections(_uid())})

    @bp.route("/api/library/collections", methods=["POST"])
    @login_required
    @_rate("30 per hour")
    def create_library_collection():
        if collection_service is None:
            return jsonify({"error": "not_configured"}), 503
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name_required"}), 400
        parent_id = data.get("parent_id")
        try:
            parent_id = int(parent_id) if parent_id not in (None, "") else None
        except (TypeError, ValueError):
            parent_id = None
        row = collection_service.create_collection(
            _uid(),
            name,
            description=str(data.get("description") or ""),
            parent_id=parent_id,
            source="manual",
        )
        if not row:
            return jsonify({"error": "create_failed"}), 400
        return jsonify(row), 201

    @bp.route("/api/library/collections/<int:cid>", methods=["GET"])
    @login_required
    def get_library_collection(cid: int):
        if collection_service is None:
            return jsonify({"error": "not_configured"}), 503
        row = collection_service.get_collection(_uid(), cid)
        if not row:
            return jsonify({"error": "not_found"}), 404
        return jsonify(row)

    @bp.route("/api/library/collections/<int:cid>", methods=["PATCH"])
    @login_required
    def patch_library_collection(cid: int):
        if collection_service is None:
            return jsonify({"error": "not_configured"}), 503
        data = request.get_json(silent=True) or {}
        kwargs = {}
        if "name" in data:
            kwargs["name"] = str(data["name"])
        if "description" in data:
            kwargs["description"] = str(data["description"])
        if "sort_order" in data:
            try:
                kwargs["sort_order"] = int(data["sort_order"])
            except (TypeError, ValueError):
                pass
        if "parent_id" in data:
            raw = data["parent_id"]
            if raw in (None, "", "null"):
                kwargs["parent_id"] = None
            else:
                try:
                    kwargs["parent_id"] = int(raw)
                except (TypeError, ValueError):
                    return jsonify({"error": "invalid_parent"}), 400
        row = collection_service.update_collection(_uid(), cid, **kwargs)
        if not row:
            return jsonify({"error": "not_found"}), 404
        return jsonify(row)

    @bp.route("/api/library/collections/<int:cid>", methods=["DELETE"])
    @login_required
    def delete_library_collection(cid: int):
        if collection_service is None:
            return jsonify({"error": "not_configured"}), 503
        ok = collection_service.delete_collection(_uid(), cid)
        if not ok:
            return jsonify({"error": "not_found"}), 404
        return jsonify({"ok": True})

    @bp.route("/api/library/collections/<int:cid>/papers", methods=["POST"])
    @login_required
    def add_collection_papers(cid: int):
        if collection_service is None:
            return jsonify({"error": "not_configured"}), 503
        data = request.get_json(silent=True) or {}
        file_ids = data.get("file_ids") or []
        if not isinstance(file_ids, list) or not file_ids:
            return jsonify({"error": "file_ids_required"}), 400
        try:
            file_ids = [int(x) for x in file_ids]
        except (TypeError, ValueError):
            return jsonify({"error": "invalid_file_ids"}), 400
        result = collection_service.add_papers(_uid(), cid, file_ids)
        if result.get("error") == "not_found":
            return jsonify(result), 404
        if result.get("error"):
            return jsonify(result), 500
        return jsonify(result)

    @bp.route("/api/library/collections/<int:cid>/papers", methods=["DELETE"])
    @login_required
    def remove_collection_papers(cid: int):
        if collection_service is None:
            return jsonify({"error": "not_configured"}), 503
        data = request.get_json(silent=True) or {}
        file_ids = data.get("file_ids") or []
        if not isinstance(file_ids, list) or not file_ids:
            return jsonify({"error": "file_ids_required"}), 400
        try:
            file_ids = [int(x) for x in file_ids]
        except (TypeError, ValueError):
            return jsonify({"error": "invalid_file_ids"}), 400
        result = collection_service.remove_papers(_uid(), cid, file_ids)
        if result.get("error") == "not_found":
            return jsonify(result), 404
        if result.get("error"):
            return jsonify(result), 500
        return jsonify(result)

    return bp
