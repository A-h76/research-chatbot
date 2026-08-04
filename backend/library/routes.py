"""HTTP routes for Library Bridge (factory, no import server)."""

from __future__ import annotations

import io
import json
import secrets
from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect, request, session

from .adapters import get_adapter
from .service import records_from_user_files
from . import zotero as zotero_mod
from . import mendeley as mendeley_mod
from . import google_drive as google_drive_mod
from . import dropbox as dropbox_mod
from . import onedrive as onedrive_mod
from .bibtex import to_bibtex
from .ris import to_ris
from security.token_crypto import seal_secret, unseal_secret
from security.request_validation import (
    RequestValidationError,
    optional_int,
    parse_json_object,
    reject_unknown_fields,
    require_string,
)


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
    sync_service=None,
    storage=None,
    enqueue_phase1=None,
    enqueue_import=None,
    upload_dir=None,
    max_file_mb=50,
    allowed_extensions=None,
    LibrarySyncRun=None,
    token_secret_key="",
    UploadJob=None,
    OutboxEvent=None,
):
    bp = Blueprint("library_bridge", __name__)
    # Prefer full import (extract + chunk + phase1); fall back to phase1-only.
    _enqueue_after_attach = enqueue_import or enqueue_phase1
    _tok_key = token_secret_key or ""
    _can_enqueue_sync = UploadJob is not None and OutboxEvent is not None

    def _seal(plain: str) -> str:
        return seal_secret(plain, secret_key=_tok_key)

    def _unseal(stored: str) -> str:
        return unseal_secret(stored, secret_key=_tok_key)

    def _store_oauth(row, *, access_token=None, access_secret=None, refresh_token=None):
        """Persist OAuth secrets encrypted at rest (Phase 4)."""
        if access_token is not None:
            row.access_token = _seal(access_token)
        if access_secret is not None:
            row.access_secret = _seal(access_secret)
        if refresh_token is not None:
            row.refresh_token = _seal(refresh_token)

    def _oauth_plain(row) -> dict:
        return {
            "access_token": _unseal(row.access_token or ""),
            "access_secret": _unseal(row.access_secret or ""),
            "refresh_token": _unseal(row.refresh_token or ""),
        }

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

    def _import_options_from_body(body: dict, *, default_project_prefix: str = "Import"):
        create_project = (
            str(body.get("create_project") or "").lower() in {"1", "true", "yes"}
            or body.get("create_project") is True
        )
        project_name = (body.get("project_name") or body.get("create_project_name") or "").strip() or None
        if create_project and not project_name:
            project_name = f"{default_project_prefix} {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        if not create_project:
            project_name = None
        try:
            pid = int(body.get("project_id")) if body.get("project_id") not in (None, "", "null") else None
        except (TypeError, ValueError):
            pid = None
        create_collection = (
            str(body.get("create_collection") or "").lower() in {"1", "true", "yes"}
            or body.get("create_collection") is True
        )
        collection_name = (body.get("collection_name") or "").strip() or None
        if create_collection and not collection_name:
            collection_name = f"{default_project_prefix} {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        if not create_collection:
            collection_name = None
        try:
            cid = int(body.get("collection_id")) if body.get("collection_id") not in (None, "", "null") else None
        except (TypeError, ValueError):
            cid = None
        return {
            "project_id": None if project_name else pid,
            "create_project_name": project_name,
            "collection_id": cid,
            "create_collection_name": collection_name,
        }

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
            g = connected.get("google_drive")
            d = connected.get("dropbox")
            od = connected.get("onedrive")
            z_meta = {}
            m_meta = {}
            g_meta = {}
            d_meta = {}
            od_meta = {}
            if z and z.meta_json:
                try:
                    z_meta = json.loads(z.meta_json)
                except Exception:
                    z_meta = {}
            if m and m.meta_json:
                try:
                    m_meta = json.loads(m.meta_json)
                except Exception:
                    m_meta = {}
            if g and g.meta_json:
                try:
                    g_meta = json.loads(g.meta_json)
                except Exception:
                    g_meta = {}
            if d and d.meta_json:
                try:
                    d_meta = json.loads(d.meta_json)
                except Exception:
                    d_meta = {}
            if od and od.meta_json:
                try:
                    od_meta = json.loads(od.meta_json)
                except Exception:
                    od_meta = {}
            return jsonify(
                {
                    "zotero": {
                        "available": zotero_mod.zotero_configured(),
                        "connected": bool(z),
                        "username": z_meta.get("username") or "",
                        "external_user_id": (z.external_user_id if z else "") or "",
                        "last_synced_at": z.last_synced_at.isoformat() if z and z.last_synced_at else None,
                        "incremental_sync": True,
                        "file_import": True,
                        "missing_env": zotero_mod.zotero_missing_env(),
                    },
                    "mendeley": {
                        "available": mendeley_mod.mendeley_configured(),
                        "connected": bool(m),
                        "coming_soon": False,
                        "username": m_meta.get("display_name") or m_meta.get("username") or "",
                        "external_user_id": (m.external_user_id if m else "") or "",
                        "last_synced_at": m.last_synced_at.isoformat() if m and m.last_synced_at else None,
                        "incremental_sync": True,
                        "file_import": True,
                        "missing_env": mendeley_mod.mendeley_missing_env(),
                    },
                    "google_drive": {
                        "available": google_drive_mod.drive_configured(),
                        "connected": bool(g),
                        "coming_soon": False,
                        "username": g_meta.get("display_name") or g_meta.get("email") or "",
                        "external_user_id": (g.external_user_id if g else "") or "",
                        "last_synced_at": g.last_synced_at.isoformat() if g and g.last_synced_at else None,
                        "incremental_sync": False,
                        "file_import": True,
                        "missing_env": google_drive_mod.drive_missing_env(),
                    },
                    "dropbox": {
                        "available": dropbox_mod.dropbox_configured(),
                        "connected": bool(d),
                        "coming_soon": False,
                        "username": d_meta.get("display_name") or d_meta.get("email") or "",
                        "external_user_id": (d.external_user_id if d else "") or "",
                        "last_synced_at": d.last_synced_at.isoformat() if d and d.last_synced_at else None,
                        "incremental_sync": False,
                        "file_import": True,
                        "missing_env": dropbox_mod.dropbox_missing_env(),
                    },
                    "onedrive": {
                        "available": onedrive_mod.onedrive_configured(),
                        "connected": bool(od),
                        "coming_soon": False,
                        "username": od_meta.get("display_name") or od_meta.get("email") or "",
                        "external_user_id": (od.external_user_id if od else "") or "",
                        "last_synced_at": od.last_synced_at.isoformat() if od and od.last_synced_at else None,
                        "incremental_sync": False,
                        "file_import": True,
                        "missing_env": onedrive_mod.onedrive_missing_env(),
                    },
                    "formats": ["bibtex", "ris"],
                    "adapters": [
                        "bibtex",
                        "ris",
                        "zotero",
                        "mendeley",
                        "openalex",
                        "google_drive",
                        "dropbox",
                        "onedrive",
                    ],
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
        try:
            adapter = get_adapter(fmt)
        except KeyError:
            return jsonify({"error": "unsupported_format", "detail": "Use bibtex or ris."}), 400

        records = adapter.fetch_records(text=text)
        source_tag = f"from-{adapter.name}"

        if not records:
            return jsonify({"error": "no_records", "detail": "No bibliographic entries found."}), 400

        body = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
        if request.files and request.is_json is False:
            raw_json = request.form.get("json")
            if raw_json:
                try:
                    body = {**body, **json.loads(raw_json)}
                except Exception:
                    pass

        opts = _import_options_from_body(body)
        result = import_service.import_records(
            _uid(),
            records,
            source_tag=source_tag,
            **opts,
        )
        if result.get("error"):
            status = 404 if result["error"] == "project_not_found" else 400
            if result["error"] == "import_failed":
                status = 500
            return jsonify(result), status
        return jsonify({**result, "format": adapter.name, "parsed": len(records)}), 201

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
                    meta_json=meta,
                    status="active",
                )
                _store_oauth(
                    row,
                    access_token=tokens.get("access_token") or "",
                    access_secret=tokens.get("access_secret") or "",
                )
                db.add(row)
            else:
                row.external_user_id = tokens.get("user_id") or row.external_user_id
                _store_oauth(
                    row,
                    access_token=tokens.get("access_token") or "",
                    access_secret=tokens.get("access_secret") or "",
                )
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
                _store_oauth(row, access_token="", access_secret="")
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
                toks = _oauth_plain(row)
                adapter = get_adapter("zotero")
                items = adapter.list_folders(
                    access_token=toks["access_token"],
                    access_secret=toks["access_secret"],
                    external_user_id=row.external_user_id,
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
        try:
            data = parse_json_object(request.get_json(silent=True))
            reject_unknown_fields(data, {"collection_key", "project_id", "limit", "create_project"})
            collection_key = require_string(data, "collection_key", max_len=200, required=False) or "all"
        except RequestValidationError as exc:
            return exc.to_response()
        coll_name = ""
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "zotero")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            try:
                toks = _oauth_plain(row)
                adapter = get_adapter("zotero")
                if collection_key not in {"all", "", "root"}:
                    z_cols = adapter.list_folders(
                        access_token=toks["access_token"],
                        access_secret=toks["access_secret"],
                        external_user_id=row.external_user_id,
                    )
                    for c in z_cols:
                        if c.get("key") == collection_key:
                            coll_name = c.get("name") or ""
                            break
                records = adapter.fetch_records(
                    access_token=toks["access_token"],
                    access_secret=toks["access_secret"],
                    external_user_id=row.external_user_id,
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

        opts = _import_options_from_body(data, default_project_prefix="Zotero")
        result = import_service.import_records(
            _uid(),
            records,
            source_tag="from-zotero",
            **opts,
        )
        if result.get("error"):
            status = 404 if result["error"] == "project_not_found" else 500
            return jsonify(result), status
        return jsonify({**result, "parsed": len(records), "source": "zotero"}), 201

    # ── Mendeley OAuth2 + import (Phase 1a one-shot) ────────────────────
    @bp.route("/api/library/mendeley/connect", methods=["GET", "POST"])
    @login_required
    @_rate("20 per hour")
    def mendeley_connect():
        if not mendeley_mod.mendeley_configured():
            return jsonify(
                {
                    "error": "mendeley_not_configured",
                    "detail": "Set MENDELEY_CLIENT_ID and MENDELEY_CLIENT_SECRET.",
                    "coming_soon": False,
                    "fallback": ["bibtex", "ris"],
                }
            ), 503
        callback = f"{app_base_url.rstrip('/')}/api/library/mendeley/callback"
        state = secrets.token_urlsafe(24)
        session["mendeley_oauth"] = {"state": state}
        try:
            started = mendeley_mod.begin_oauth(callback, state)
        except Exception as exc:
            return jsonify({"error": "oauth_start_failed", "detail": str(exc)[:200]}), 502
        if request.method == "GET" and request.args.get("redirect") == "1":
            return redirect(started["authorize_url"])
        return jsonify({"authorize_url": started["authorize_url"]})

    @bp.route("/api/library/mendeley/callback", methods=["GET"])
    @login_required
    def mendeley_callback():
        if not mendeley_mod.mendeley_configured():
            return redirect("/library?mendeley=not_configured")
        pending = session.pop("mendeley_oauth", None) or {}
        code = (request.args.get("code") or "").strip()
        state = (request.args.get("state") or "").strip()
        if not code or not pending.get("state") or state != pending.get("state"):
            return redirect("/library?mendeley=denied")
        callback = f"{app_base_url.rstrip('/')}/api/library/mendeley/callback"
        try:
            tokens = mendeley_mod.finish_oauth(code=code, callback_uri=callback)
            profile = mendeley_mod.fetch_profile(tokens["access_token"])
        except Exception:
            return redirect("/library?mendeley=error")

        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "mendeley")
            meta = json.dumps({"display_name": profile.get("display_name") or ""})
            if not row:
                row = LibraryConnection(
                    user_id=_uid(),
                    provider="mendeley",
                    external_user_id=profile.get("id") or "",
                    meta_json=meta,
                    status="active",
                )
                _store_oauth(
                    row,
                    access_token=tokens.get("access_token") or "",
                    access_secret="",
                    refresh_token=tokens.get("refresh_token") or "",
                )
                db.add(row)
            else:
                row.external_user_id = profile.get("id") or row.external_user_id
                _store_oauth(
                    row,
                    access_token=tokens.get("access_token") or "",
                    refresh_token=tokens.get("refresh_token") or _oauth_plain(row)["refresh_token"],
                )
                row.meta_json = meta
                row.status = "active"
                row.updated_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()
        return redirect("/library?mendeley=connected")

    @bp.route("/api/library/mendeley/disconnect", methods=["POST"])
    @login_required
    def mendeley_disconnect():
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "mendeley")
            if row:
                row.status = "revoked"
                _store_oauth(row, access_token="", refresh_token="")
                row.updated_at = datetime.now(timezone.utc)
                db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    def _mendeley_access_token(db, row) -> str:
        toks = _oauth_plain(row)
        token = (toks["access_token"] or "").strip()
        if token:
            return token
        refresh = (toks["refresh_token"] or "").strip()
        if not refresh:
            return ""
        refreshed = mendeley_mod.refresh_access_token(refresh)
        _store_oauth(
            row,
            access_token=refreshed.get("access_token") or "",
            refresh_token=refreshed.get("refresh_token") or refresh,
        )
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        return _oauth_plain(row)["access_token"] or ""

    @bp.route("/api/library/mendeley/folders", methods=["GET"])
    @login_required
    def mendeley_folders():
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "mendeley")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            try:
                token = _mendeley_access_token(db, row)
                if not token:
                    return jsonify({"error": "not_connected"}), 400
                adapter = get_adapter("mendeley")
                items = adapter.list_folders(access_token=token)
            except Exception as exc:
                refresh = _oauth_plain(row)["refresh_token"]
                if refresh:
                    try:
                        refreshed = mendeley_mod.refresh_access_token(refresh)
                        _store_oauth(
                            row,
                            access_token=refreshed.get("access_token") or "",
                            refresh_token=refreshed.get("refresh_token") or refresh,
                        )
                        row.updated_at = datetime.now(timezone.utc)
                        db.commit()
                        adapter = get_adapter("mendeley")
                        items = adapter.list_folders(access_token=_oauth_plain(row)["access_token"])
                        return jsonify({"items": items})
                    except Exception as exc2:
                        return jsonify({"error": "mendeley_api_error", "detail": str(exc2)[:200]}), 502
                return jsonify({"error": "mendeley_api_error", "detail": str(exc)[:200]}), 502
            return jsonify({"items": items})
        finally:
            db.close()

    @bp.route("/api/library/mendeley/import", methods=["POST"])
    @login_required
    @_rate("5 per hour")
    def mendeley_import():
        try:
            data = parse_json_object(request.get_json(silent=True))
            reject_unknown_fields(
                data, {"folder_id", "collection_key", "project_id", "limit", "create_project"}
            )
            folder_id = (
                require_string(data, "folder_id", max_len=200, required=False)
                or require_string(data, "collection_key", max_len=200, required=False)
                or "all"
            )
        except RequestValidationError as exc:
            return exc.to_response()
        folder_name = ""
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "mendeley")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            try:
                token = _mendeley_access_token(db, row)
                if not token:
                    return jsonify({"error": "not_connected"}), 400
                adapter = get_adapter("mendeley")
                if folder_id not in {"all", "", "root"}:
                    folders = adapter.list_folders(access_token=token)
                    for f in folders:
                        if f.get("key") == folder_id:
                            folder_name = f.get("name") or ""
                            break
                records = adapter.fetch_records(
                    access_token=token,
                    folder_id=folder_id,
                    folder_name=folder_name,
                    limit=int(data.get("limit") or 200),
                )
            except Exception as exc:
                return jsonify({"error": "mendeley_api_error", "detail": str(exc)[:200]}), 502
        finally:
            db.close()

        if not records:
            return jsonify({"error": "no_records", "detail": "No documents in that folder."}), 400

        opts = _import_options_from_body(data, default_project_prefix="Mendeley")
        result = import_service.import_records(
            _uid(),
            records,
            source_tag="from-mendeley",
            **opts,
        )
        if result.get("error"):
            status = 404 if result["error"] == "project_not_found" else 500
            return jsonify(result), status
        return jsonify({**result, "parsed": len(records), "source": "mendeley"}), 201

    # ── Google Drive OAuth + PDF import (Golden Rule) ───────────────────
    @bp.route("/api/library/google_drive/connect", methods=["GET", "POST"])
    @login_required
    @_rate("20 per hour")
    def google_drive_connect():
        if not google_drive_mod.drive_configured():
            return jsonify(
                {
                    "error": "google_drive_not_configured",
                    "detail": "Set GOOGLE_DRIVE_CLIENT_ID/SECRET (or GOOGLE_CLIENT_ID/SECRET).",
                    "coming_soon": False,
                    "missing_env": google_drive_mod.drive_missing_env(),
                    "fallback": ["bibtex", "ris", "upload"],
                }
            ), 503
        callback = google_drive_mod.oauth_redirect_uri(app_base_url)
        state = secrets.token_urlsafe(24)
        session["google_drive_oauth"] = {"state": state}
        try:
            started = google_drive_mod.begin_oauth(callback, state)
        except Exception as exc:
            return jsonify({"error": "oauth_start_failed", "detail": str(exc)[:200]}), 502
        # Integrations card navigates GET to this path — redirect into Google.
        if request.method == "GET":
            return redirect(started["authorize_url"])
        return jsonify({"authorize_url": started["authorize_url"]})

    @bp.route("/api/library/google_drive/callback", methods=["GET"])
    @login_required
    def google_drive_callback():
        if not google_drive_mod.drive_configured():
            return redirect("/library?google_drive=not_configured")
        pending = session.pop("google_drive_oauth", None) or {}
        code = (request.args.get("code") or "").strip()
        state = (request.args.get("state") or "").strip()
        if not code or not pending.get("state") or state != pending.get("state"):
            return redirect("/library?google_drive=denied")
        callback = google_drive_mod.oauth_redirect_uri(app_base_url)
        try:
            tokens = google_drive_mod.finish_oauth(code=code, callback_uri=callback)
            profile = google_drive_mod.fetch_profile(tokens["access_token"])
        except Exception:
            return redirect("/library?google_drive=error")

        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "google_drive")
            meta = json.dumps(
                {
                    "display_name": profile.get("display_name") or "",
                    "email": profile.get("email") or "",
                }
            )
            if not row:
                row = LibraryConnection(
                    user_id=_uid(),
                    provider="google_drive",
                    external_user_id=profile.get("id") or "",
                    meta_json=meta,
                    status="active",
                )
                _store_oauth(
                    row,
                    access_token=tokens.get("access_token") or "",
                    access_secret="",
                    refresh_token=tokens.get("refresh_token") or "",
                )
                db.add(row)
            else:
                row.external_user_id = profile.get("id") or row.external_user_id
                _store_oauth(
                    row,
                    access_token=tokens.get("access_token") or "",
                    refresh_token=tokens.get("refresh_token")
                    or _oauth_plain(row)["refresh_token"],
                )
                row.meta_json = meta
                row.status = "active"
                row.updated_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()
        return redirect("/library?provider=google_drive&google_drive=connected#import")

    @bp.route("/api/library/google_drive/disconnect", methods=["POST"])
    @login_required
    def google_drive_disconnect():
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "google_drive")
            if row:
                row.status = "revoked"
                _store_oauth(row, access_token="", refresh_token="")
                row.updated_at = datetime.now(timezone.utc)
                db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    def _google_drive_access_token(db, row) -> str:
        toks = _oauth_plain(row)
        token = (toks["access_token"] or "").strip()
        if token:
            return token
        refresh = (toks["refresh_token"] or "").strip()
        if not refresh:
            return ""
        refreshed = google_drive_mod.refresh_access_token(refresh)
        _store_oauth(
            row,
            access_token=refreshed.get("access_token") or "",
            refresh_token=refreshed.get("refresh_token") or refresh,
        )
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        return _oauth_plain(row)["access_token"] or ""

    @bp.route("/api/library/google_drive/folders", methods=["GET"])
    @login_required
    def google_drive_folders():
        parent_id = (request.args.get("parent_id") or "root").strip() or "root"
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "google_drive")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            try:
                token = _google_drive_access_token(db, row)
                if not token:
                    return jsonify({"error": "not_connected"}), 400
                items = google_drive_mod.list_folders(token, parent_id=parent_id)
                return jsonify({"items": items, "parent_id": parent_id})
            except Exception as exc:
                return jsonify({"error": "google_drive_api_error", "detail": str(exc)[:200]}), 502
        finally:
            db.close()

    @bp.route("/api/library/google_drive/files", methods=["GET"])
    @login_required
    def google_drive_files():
        folder_id = (request.args.get("folder_id") or "root").strip() or "root"
        page_token = (request.args.get("page_token") or "").strip()
        limit = min(100, max(1, int(request.args.get("limit") or 50)))
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "google_drive")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            try:
                token = _google_drive_access_token(db, row)
                if not token:
                    return jsonify({"error": "not_connected"}), 400
                payload = google_drive_mod.list_pdf_files(
                    token,
                    folder_id=folder_id,
                    limit=limit,
                    page_token=page_token,
                )
                return jsonify(payload)
            except Exception as exc:
                return jsonify({"error": "google_drive_api_error", "detail": str(exc)[:200]}), 502
        finally:
            db.close()

    @bp.route("/api/library/google_drive/import", methods=["POST"])
    @login_required
    @_rate("10 per hour")
    def google_drive_import():
        """Import selected Drive PDFs into Library → shared import job (Golden Rule)."""
        from backend.library.file_pull import apply_pdf_bytes_to_stub

        try:
            data = parse_json_object(request.get_json(silent=True))
            reject_unknown_fields(
                data, {"file_ids", "project_id", "folder_id", "create_project", "project_name"}
            )
        except RequestValidationError as exc:
            return exc.to_response()

        raw_ids = data.get("file_ids") or []
        if not isinstance(raw_ids, list) or not raw_ids:
            return jsonify({"error": "file_ids_required"}), 400
        file_ids = [str(x).strip() for x in raw_ids if str(x).strip()][:20]
        if not file_ids:
            return jsonify({"error": "file_ids_required"}), 400

        project_id = data.get("project_id")
        if project_id is not None:
            try:
                project_id = int(project_id)
            except (TypeError, ValueError):
                project_id = None

        uid = _uid()
        if storage is None or not upload_dir or _enqueue_after_attach is None:
            return jsonify({"error": "pipeline_not_wired"}), 503

        db = SessionLocal()
        created_ids: list[int] = []
        queued_n = 0
        skipped: list[dict] = []
        errors: list[dict] = []
        try:
            if project_id is not None:
                proj = db.get(Project, project_id)
                if not proj or proj.user_id != uid:
                    return jsonify({"error": "project_not_found"}), 404

            row = _get_connection(db, uid, "google_drive")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            token = _google_drive_access_token(db, row)
            if not token:
                return jsonify({"error": "not_connected"}), 400

            for ext_id in file_ids:
                existing = (
                    db.execute(
                        select_fn(UserFile).where(
                            UserFile.user_id == uid,
                            UserFile.external_provider == "google_drive",
                            UserFile.external_item_id == ext_id,
                        )
                    )
                    .scalars()
                    .first()
                )
                if existing:
                    skipped.append(
                        {
                            "external_id": ext_id,
                            "reason": "already_exists",
                            "file_id": existing.id,
                        }
                    )
                    continue

                hit = google_drive_mod.download_file(
                    token,
                    ext_id,
                    max_bytes=int(max_file_mb or 50) * 1024 * 1024,
                )
                if not hit:
                    errors.append({"external_id": ext_id, "error": "download_failed"})
                    continue
                pdf_bytes, filename, content_type = hit

                uf = UserFile(
                    user_id=uid,
                    project_id=project_id,
                    conversation_id=None,
                    name=filename[:300],
                    mime="",
                    kind="document",
                    path="",
                    size=0,
                    title=filename.rsplit(".", 1)[0][:500],
                    authors="",
                    year="",
                    venue="",
                    doi="",
                    abstract="",
                    reading_status="unread",
                    tags=json.dumps(["from-google-drive", f"gdrive:{ext_id[:80]}"]),
                    meta_status="pending",
                    metadata_source="google_drive",
                    source_url="",
                    doi_verified=False,
                    external_provider="google_drive",
                    external_item_id=ext_id[:120],
                )
                db.add(uf)
                db.flush()

                applied = apply_pdf_bytes_to_stub(
                    db,
                    uf,
                    data=pdf_bytes,
                    filename=filename,
                    content_type=content_type,
                    storage=storage,
                    upload_dir=upload_dir,
                    enqueue_import=_enqueue_after_attach,
                    user_id=uid,
                    max_file_mb=max_file_mb,
                )
                if applied.get("ok"):
                    created_ids.append(uf.id)
                    if applied.get("queued"):
                        queued_n += 1
                else:
                    errors.append(
                        {
                            "external_id": ext_id,
                            "error": applied.get("error") or "attach_failed",
                            "file_id": uf.id,
                        }
                    )

            db.commit()
            return (
                jsonify(
                    {
                        "ok": True,
                        "source": "google_drive",
                        "created": len(created_ids),
                        "created_ids": created_ids,
                        "queued": queued_n,
                        "skipped": skipped,
                        "errors": errors,
                        "project_id": project_id,
                        "analysis_queued": queued_n > 0,
                    }
                ),
                201,
            )
        except Exception as exc:
            db.rollback()
            return jsonify({"error": "import_failed", "detail": str(exc)[:200]}), 500
        finally:
            db.close()

    # ── Dropbox OAuth + PDF import (Golden Rule) ────────────────────────
    @bp.route("/api/library/dropbox/connect", methods=["GET", "POST"])
    @login_required
    @_rate("20 per hour")
    def dropbox_connect():
        if not dropbox_mod.dropbox_configured():
            return jsonify(
                {
                    "error": "dropbox_not_configured",
                    "detail": "Set DROPBOX_CLIENT_ID and DROPBOX_CLIENT_SECRET.",
                    "coming_soon": False,
                    "missing_env": dropbox_mod.dropbox_missing_env(),
                    "fallback": ["bibtex", "ris", "upload"],
                }
            ), 503
        callback = dropbox_mod.oauth_redirect_uri(app_base_url)
        state = secrets.token_urlsafe(24)
        session["dropbox_oauth"] = {"state": state}
        try:
            started = dropbox_mod.begin_oauth(callback, state)
        except Exception as exc:
            return jsonify({"error": "oauth_start_failed", "detail": str(exc)[:200]}), 502
        if request.method == "GET":
            return redirect(started["authorize_url"])
        return jsonify({"authorize_url": started["authorize_url"]})

    @bp.route("/api/library/dropbox/callback", methods=["GET"])
    @login_required
    def dropbox_callback():
        if not dropbox_mod.dropbox_configured():
            return redirect("/library?dropbox=not_configured")
        pending = session.pop("dropbox_oauth", None) or {}
        code = (request.args.get("code") or "").strip()
        state = (request.args.get("state") or "").strip()
        if not code or not pending.get("state") or state != pending.get("state"):
            return redirect("/library?dropbox=denied")
        callback = dropbox_mod.oauth_redirect_uri(app_base_url)
        try:
            tokens = dropbox_mod.finish_oauth(code=code, callback_uri=callback)
            profile = dropbox_mod.fetch_profile(tokens["access_token"])
        except Exception:
            return redirect("/library?dropbox=error")

        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "dropbox")
            meta = json.dumps(
                {
                    "display_name": profile.get("display_name") or "",
                    "email": profile.get("email") or "",
                }
            )
            if not row:
                row = LibraryConnection(
                    user_id=_uid(),
                    provider="dropbox",
                    external_user_id=profile.get("id") or "",
                    meta_json=meta,
                    status="active",
                )
                _store_oauth(
                    row,
                    access_token=tokens.get("access_token") or "",
                    access_secret="",
                    refresh_token=tokens.get("refresh_token") or "",
                )
                db.add(row)
            else:
                row.external_user_id = profile.get("id") or row.external_user_id
                _store_oauth(
                    row,
                    access_token=tokens.get("access_token") or "",
                    refresh_token=tokens.get("refresh_token")
                    or _oauth_plain(row)["refresh_token"],
                )
                row.meta_json = meta
                row.status = "active"
                row.updated_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()
        return redirect("/library?provider=dropbox&dropbox=connected#import")

    @bp.route("/api/library/dropbox/disconnect", methods=["POST"])
    @login_required
    def dropbox_disconnect():
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "dropbox")
            if row:
                row.status = "revoked"
                _store_oauth(row, access_token="", refresh_token="")
                row.updated_at = datetime.now(timezone.utc)
                db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    def _dropbox_access_token(db, row) -> str:
        toks = _oauth_plain(row)
        token = (toks["access_token"] or "").strip()
        if token:
            return token
        refresh = (toks["refresh_token"] or "").strip()
        if not refresh:
            return ""
        refreshed = dropbox_mod.refresh_access_token(refresh)
        _store_oauth(
            row,
            access_token=refreshed.get("access_token") or "",
            refresh_token=refreshed.get("refresh_token") or refresh,
        )
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        return _oauth_plain(row)["access_token"] or ""

    @bp.route("/api/library/dropbox/folders", methods=["GET"])
    @login_required
    def dropbox_folders():
        parent_id = (request.args.get("parent_id") or "").strip()
        if parent_id in ("root", "/"):
            parent_id = ""
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "dropbox")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            try:
                token = _dropbox_access_token(db, row)
                if not token:
                    return jsonify({"error": "not_connected"}), 400
                items = dropbox_mod.list_folders(token, parent_id=parent_id)
                return jsonify({"items": items, "parent_id": parent_id or "root"})
            except Exception as exc:
                return jsonify({"error": "dropbox_api_error", "detail": str(exc)[:200]}), 502
        finally:
            db.close()

    @bp.route("/api/library/dropbox/files", methods=["GET"])
    @login_required
    def dropbox_files():
        folder_id = (request.args.get("folder_id") or "").strip()
        if folder_id in ("root", "/"):
            folder_id = ""
        page_token = (request.args.get("page_token") or "").strip()
        limit = min(100, max(1, int(request.args.get("limit") or 50)))
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "dropbox")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            try:
                token = _dropbox_access_token(db, row)
                if not token:
                    return jsonify({"error": "not_connected"}), 400
                payload = dropbox_mod.list_pdf_files(
                    token,
                    folder_id=folder_id,
                    limit=limit,
                    page_token=page_token,
                )
                return jsonify(payload)
            except Exception as exc:
                return jsonify({"error": "dropbox_api_error", "detail": str(exc)[:200]}), 502
        finally:
            db.close()

    @bp.route("/api/library/dropbox/import", methods=["POST"])
    @login_required
    @_rate("10 per hour")
    def dropbox_import():
        """Import selected Dropbox PDFs into Library → shared import job (Golden Rule)."""
        from backend.library.file_pull import apply_pdf_bytes_to_stub

        try:
            data = parse_json_object(request.get_json(silent=True))
            reject_unknown_fields(
                data, {"file_ids", "project_id", "folder_id", "create_project", "project_name"}
            )
        except RequestValidationError as exc:
            return exc.to_response()

        raw_ids = data.get("file_ids") or []
        if not isinstance(raw_ids, list) or not raw_ids:
            return jsonify({"error": "file_ids_required"}), 400
        file_ids = [str(x).strip() for x in raw_ids if str(x).strip()][:20]
        if not file_ids:
            return jsonify({"error": "file_ids_required"}), 400

        project_id = data.get("project_id")
        if project_id is not None:
            try:
                project_id = int(project_id)
            except (TypeError, ValueError):
                project_id = None

        uid = _uid()
        if storage is None or not upload_dir or _enqueue_after_attach is None:
            return jsonify({"error": "pipeline_not_wired"}), 503

        db = SessionLocal()
        created_ids: list[int] = []
        queued_n = 0
        skipped: list[dict] = []
        errors: list[dict] = []
        try:
            if project_id is not None:
                proj = db.get(Project, project_id)
                if not proj or proj.user_id != uid:
                    return jsonify({"error": "project_not_found"}), 404

            row = _get_connection(db, uid, "dropbox")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            token = _dropbox_access_token(db, row)
            if not token:
                return jsonify({"error": "not_connected"}), 400

            for ext_id in file_ids:
                existing = (
                    db.execute(
                        select_fn(UserFile).where(
                            UserFile.user_id == uid,
                            UserFile.external_provider == "dropbox",
                            UserFile.external_item_id == ext_id,
                        )
                    )
                    .scalars()
                    .first()
                )
                if existing:
                    skipped.append(
                        {
                            "external_id": ext_id,
                            "reason": "already_exists",
                            "file_id": existing.id,
                        }
                    )
                    continue

                hit = dropbox_mod.download_file(
                    token,
                    ext_id,
                    max_bytes=int(max_file_mb or 50) * 1024 * 1024,
                )
                if not hit:
                    errors.append({"external_id": ext_id, "error": "download_failed"})
                    continue
                pdf_bytes, filename, content_type = hit

                uf = UserFile(
                    user_id=uid,
                    project_id=project_id,
                    conversation_id=None,
                    name=filename[:300],
                    mime="",
                    kind="document",
                    path="",
                    size=0,
                    title=filename.rsplit(".", 1)[0][:500],
                    authors="",
                    year="",
                    venue="",
                    doi="",
                    abstract="",
                    reading_status="unread",
                    tags=json.dumps(["from-dropbox", f"dropbox:{ext_id[:80]}"]),
                    meta_status="pending",
                    metadata_source="dropbox",
                    source_url="",
                    doi_verified=False,
                    external_provider="dropbox",
                    external_item_id=ext_id[:120],
                )
                db.add(uf)
                db.flush()

                applied = apply_pdf_bytes_to_stub(
                    db,
                    uf,
                    data=pdf_bytes,
                    filename=filename,
                    content_type=content_type,
                    storage=storage,
                    upload_dir=upload_dir,
                    enqueue_import=_enqueue_after_attach,
                    user_id=uid,
                    max_file_mb=max_file_mb,
                )
                if applied.get("ok"):
                    created_ids.append(uf.id)
                    if applied.get("queued"):
                        queued_n += 1
                else:
                    errors.append(
                        {
                            "external_id": ext_id,
                            "error": applied.get("error") or "attach_failed",
                            "file_id": uf.id,
                        }
                    )

            db.commit()
            return (
                jsonify(
                    {
                        "ok": True,
                        "source": "dropbox",
                        "created": len(created_ids),
                        "created_ids": created_ids,
                        "queued": queued_n,
                        "skipped": skipped,
                        "errors": errors,
                        "project_id": project_id,
                        "analysis_queued": queued_n > 0,
                    }
                ),
                201,
            )
        except Exception as exc:
            db.rollback()
            return jsonify({"error": "import_failed", "detail": str(exc)[:200]}), 500
        finally:
            db.close()

    @bp.route("/api/library/onedrive/connect", methods=["GET", "POST"])
    @login_required
    @_rate("20 per hour")
    def onedrive_connect():
        if not onedrive_mod.onedrive_configured():
            return jsonify(
                {
                    "error": "onedrive_not_configured",
                    "detail": "Set ONEDRIVE_CLIENT_ID and ONEDRIVE_CLIENT_SECRET.",
                    "coming_soon": False,
                    "missing_env": onedrive_mod.onedrive_missing_env(),
                    "fallback": ["bibtex", "ris", "upload"],
                }
            ), 503
        callback = onedrive_mod.oauth_redirect_uri(app_base_url)
        state = secrets.token_urlsafe(24)
        session["onedrive_oauth"] = {"state": state}
        try:
            started = onedrive_mod.begin_oauth(callback, state)
        except Exception as exc:
            return jsonify({"error": "oauth_start_failed", "detail": str(exc)[:200]}), 502
        if request.method == "GET":
            return redirect(started["authorize_url"])
        return jsonify({"authorize_url": started["authorize_url"]})

    @bp.route("/api/library/onedrive/callback", methods=["GET"])
    @login_required
    def onedrive_callback():
        if not onedrive_mod.onedrive_configured():
            return redirect("/library?onedrive=not_configured")
        pending = session.pop("onedrive_oauth", None) or {}
        code = (request.args.get("code") or "").strip()
        state = (request.args.get("state") or "").strip()
        if not code or not pending.get("state") or state != pending.get("state"):
            return redirect("/library?onedrive=denied")
        callback = onedrive_mod.oauth_redirect_uri(app_base_url)
        try:
            tokens = onedrive_mod.finish_oauth(code=code, callback_uri=callback)
            profile = onedrive_mod.fetch_profile(tokens["access_token"])
        except Exception:
            return redirect("/library?onedrive=error")

        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "onedrive")
            meta = json.dumps(
                {
                    "display_name": profile.get("display_name") or "",
                    "email": profile.get("email") or "",
                }
            )
            if not row:
                row = LibraryConnection(
                    user_id=_uid(),
                    provider="onedrive",
                    external_user_id=profile.get("id") or "",
                    meta_json=meta,
                    status="active",
                )
                _store_oauth(
                    row,
                    access_token=tokens.get("access_token") or "",
                    access_secret="",
                    refresh_token=tokens.get("refresh_token") or "",
                )
                db.add(row)
            else:
                row.external_user_id = profile.get("id") or row.external_user_id
                _store_oauth(
                    row,
                    access_token=tokens.get("access_token") or "",
                    refresh_token=tokens.get("refresh_token")
                    or _oauth_plain(row)["refresh_token"],
                )
                row.meta_json = meta
                row.status = "active"
                row.updated_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()
        return redirect("/library?provider=onedrive&onedrive=connected#import")

    @bp.route("/api/library/onedrive/disconnect", methods=["POST"])
    @login_required
    def onedrive_disconnect():
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "onedrive")
            if row:
                row.status = "revoked"
                _store_oauth(row, access_token="", refresh_token="")
                row.updated_at = datetime.now(timezone.utc)
                db.commit()
            return jsonify({"ok": True})
        finally:
            db.close()

    def _onedrive_access_token(db, row) -> str:
        toks = _oauth_plain(row)
        token = (toks["access_token"] or "").strip()
        if token:
            return token
        refresh = (toks["refresh_token"] or "").strip()
        if not refresh:
            return ""
        refreshed = onedrive_mod.refresh_access_token(refresh)
        _store_oauth(
            row,
            access_token=refreshed.get("access_token") or "",
            refresh_token=refreshed.get("refresh_token") or refresh,
        )
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        return _oauth_plain(row)["access_token"] or ""

    @bp.route("/api/library/onedrive/folders", methods=["GET"])
    @login_required
    def onedrive_folders():
        parent_id = (request.args.get("parent_id") or "root").strip() or "root"
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "onedrive")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            try:
                token = _onedrive_access_token(db, row)
                if not token:
                    return jsonify({"error": "not_connected"}), 400
                items = onedrive_mod.list_folders(token, parent_id=parent_id)
                return jsonify({"items": items, "parent_id": parent_id})
            except Exception as exc:
                return jsonify({"error": "onedrive_api_error", "detail": str(exc)[:200]}), 502
        finally:
            db.close()

    @bp.route("/api/library/onedrive/files", methods=["GET"])
    @login_required
    def onedrive_files():
        folder_id = (request.args.get("folder_id") or "root").strip() or "root"
        page_token = (request.args.get("page_token") or "").strip()
        limit = min(100, max(1, int(request.args.get("limit") or 50)))
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), "onedrive")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            try:
                token = _onedrive_access_token(db, row)
                if not token:
                    return jsonify({"error": "not_connected"}), 400
                payload = onedrive_mod.list_pdf_files(
                    token,
                    folder_id=folder_id,
                    limit=limit,
                    page_token=page_token,
                )
                return jsonify(payload)
            except Exception as exc:
                return jsonify({"error": "onedrive_api_error", "detail": str(exc)[:200]}), 502
        finally:
            db.close()

    @bp.route("/api/library/onedrive/import", methods=["POST"])
    @login_required
    @_rate("10 per hour")
    def onedrive_import():
        """Import selected OneDrive PDFs into Library → shared import job (Golden Rule)."""
        from backend.library.file_pull import apply_pdf_bytes_to_stub

        try:
            data = parse_json_object(request.get_json(silent=True))
            reject_unknown_fields(
                data, {"file_ids", "project_id", "folder_id", "create_project", "project_name"}
            )
        except RequestValidationError as exc:
            return exc.to_response()

        raw_ids = data.get("file_ids") or []
        if not isinstance(raw_ids, list) or not raw_ids:
            return jsonify({"error": "file_ids_required"}), 400
        file_ids = [str(x).strip() for x in raw_ids if str(x).strip()][:20]
        if not file_ids:
            return jsonify({"error": "file_ids_required"}), 400

        project_id = data.get("project_id")
        if project_id is not None:
            try:
                project_id = int(project_id)
            except (TypeError, ValueError):
                project_id = None

        uid = _uid()
        if storage is None or not upload_dir or _enqueue_after_attach is None:
            return jsonify({"error": "pipeline_not_wired"}), 503

        db = SessionLocal()
        created_ids: list[int] = []
        queued_n = 0
        skipped: list[dict] = []
        errors: list[dict] = []
        try:
            if project_id is not None:
                proj = db.get(Project, project_id)
                if not proj or proj.user_id != uid:
                    return jsonify({"error": "project_not_found"}), 404

            row = _get_connection(db, uid, "onedrive")
            if not row:
                return jsonify({"error": "not_connected"}), 400
            token = _onedrive_access_token(db, row)
            if not token:
                return jsonify({"error": "not_connected"}), 400

            for ext_id in file_ids:
                existing = (
                    db.execute(
                        select_fn(UserFile).where(
                            UserFile.user_id == uid,
                            UserFile.external_provider == "onedrive",
                            UserFile.external_item_id == ext_id,
                        )
                    )
                    .scalars()
                    .first()
                )
                if existing:
                    skipped.append(
                        {
                            "external_id": ext_id,
                            "reason": "already_exists",
                            "file_id": existing.id,
                        }
                    )
                    continue

                hit = onedrive_mod.download_file(
                    token,
                    ext_id,
                    max_bytes=int(max_file_mb or 50) * 1024 * 1024,
                )
                if not hit:
                    errors.append({"external_id": ext_id, "error": "download_failed"})
                    continue
                pdf_bytes, filename, content_type = hit

                uf = UserFile(
                    user_id=uid,
                    project_id=project_id,
                    conversation_id=None,
                    name=filename[:300],
                    mime="",
                    kind="document",
                    path="",
                    size=0,
                    title=filename.rsplit(".", 1)[0][:500],
                    authors="",
                    year="",
                    venue="",
                    doi="",
                    abstract="",
                    reading_status="unread",
                    tags=json.dumps(["from-onedrive", f"onedrive:{ext_id[:80]}"]),
                    meta_status="pending",
                    metadata_source="onedrive",
                    source_url="",
                    doi_verified=False,
                    external_provider="onedrive",
                    external_item_id=ext_id[:120],
                )
                db.add(uf)
                db.flush()

                applied = apply_pdf_bytes_to_stub(
                    db,
                    uf,
                    data=pdf_bytes,
                    filename=filename,
                    content_type=content_type,
                    storage=storage,
                    upload_dir=upload_dir,
                    enqueue_import=_enqueue_after_attach,
                    user_id=uid,
                    max_file_mb=max_file_mb,
                )
                if applied.get("ok"):
                    created_ids.append(uf.id)
                    if applied.get("queued"):
                        queued_n += 1
                else:
                    errors.append(
                        {
                            "external_id": ext_id,
                            "error": applied.get("error") or "attach_failed",
                            "file_id": uf.id,
                        }
                    )

            db.commit()
            return (
                jsonify(
                    {
                        "ok": True,
                        "source": "onedrive",
                        "created": len(created_ids),
                        "created_ids": created_ids,
                        "queued": queued_n,
                        "skipped": skipped,
                        "errors": errors,
                        "project_id": project_id,
                        "analysis_queued": queued_n > 0,
                    }
                ),
                201,
            )
        except Exception as exc:
            db.rollback()
            return jsonify({"error": "import_failed", "detail": str(exc)[:200]}), 500
        finally:
            db.close()

    def _run_provider_sync(provider: str):
        """Enqueue Phase 1b incremental sync (worker-backed).

        Body ``sync: true`` runs inline (tests / no worker).
        Returns 202 + job_id / sync_run_id for async path.
        """
        from .sync import execute_provider_sync

        if sync_service is None:
            return jsonify({"error": "sync_not_configured"}), 503
        data = request.get_json(silent=True) or {}
        limit = int(data.get("limit") or 200)
        inline = bool(data.get("sync"))
        uid = _uid()

        active = sync_service.has_active_run(uid, provider)
        if active and not inline:
            return (
                jsonify(
                    {
                        "error": "sync_already_running",
                        "detail": "A sync is already queued or running for this provider.",
                        "sync_run_id": active["id"],
                        "job_id": active.get("job_id"),
                        "status": active["status"],
                    }
                ),
                409,
            )

        db = SessionLocal()
        try:
            row = _get_connection(db, uid, provider)
            if not row:
                return jsonify({"error": "not_connected"}), 400
            cursor_before = row.sync_cursor or ""
            connection_id = row.id
            token_kwargs = {}
            if provider == "zotero":
                toks = _oauth_plain(row)
                token_kwargs = {
                    "access_token": toks["access_token"],
                    "access_secret": toks["access_secret"],
                    "external_user_id": row.external_user_id,
                }
            else:
                token = _mendeley_access_token(db, row)
                if not token:
                    return jsonify({"error": "not_connected"}), 400
                token_kwargs = {"access_token": token}
        finally:
            db.close()

        # Inline path (tests / forced sync) — blocks HTTP like Phase 1b before.
        if inline or not _can_enqueue_sync:
            try:
                result = execute_provider_sync(
                    sync_service=sync_service,
                    SessionLocal=SessionLocal,
                    LibraryConnection=LibraryConnection,
                    user_id=uid,
                    provider=provider,
                    connection_id=connection_id,
                    cursor_before=cursor_before,
                    token_kwargs=token_kwargs,
                    limit=limit,
                )
                return jsonify(result)
            except Exception as exc:
                return jsonify({"error": f"{provider}_sync_failed", "detail": str(exc)[:200]}), 502

        # Async: queue UploadJob + LibrarySyncRun (status=queued).
        run_id = sync_service.start_run(
            uid,
            connection_id,
            provider,
            cursor_before,
            status="queued",
            detail={"phase": "queued"},
        )
        db = SessionLocal()
        try:
            job = UploadJob(
                file_id=None,
                user_id=uid,
                job_type="library_sync",
                status="pending",
            )
            db.add(job)
            db.flush()
            payload = {
                "type": "library_sync",
                "provider": provider,
                "connection_id": connection_id,
                "sync_run_id": run_id,
                "limit": limit,
                "cursor_before": cursor_before,
                # Tokens stay on LibraryConnection — worker reloads + unseals.
            }
            db.add(
                OutboxEvent(
                    aggregate_type="upload_job",
                    aggregate_id=job.id,
                    event_type="job.enqueued",
                    payload=json.dumps(payload, ensure_ascii=False),
                )
            )
            db.commit()
            job_id = job.id
        except Exception as exc:
            db.rollback()
            sync_service.finish_run(
                run_id,
                status="error",
                error_text=f"enqueue_failed: {exc}"[:500],
                cursor_after=cursor_before,
            )
            return jsonify({"error": "enqueue_failed", "detail": str(exc)[:200]}), 500
        finally:
            db.close()

        sync_service.patch_run_detail(run_id, {"job_id": job_id, "phase": "queued"})
        return (
            jsonify(
                {
                    "status": "queued",
                    "provider": provider,
                    "job_id": job_id,
                    "sync_run_id": run_id,
                }
            ),
            202,
        )

    @bp.route("/api/library/zotero/sync", methods=["POST"])
    @login_required
    @_rate("10 per hour")
    def zotero_sync():
        return _run_provider_sync("zotero")

    @bp.route("/api/library/mendeley/sync", methods=["POST"])
    @login_required
    @_rate("10 per hour")
    def mendeley_sync():
        return _run_provider_sync("mendeley")

    @bp.route("/api/library/sync/runs", methods=["GET"])
    @login_required
    def list_sync_runs():
        if sync_service is None:
            return jsonify({"items": []})
        provider = (request.args.get("provider") or "").strip() or None
        try:
            limit = max(1, min(50, int(request.args.get("limit", 20))))
        except (TypeError, ValueError):
            limit = 20
        return jsonify({"items": sync_service.list_runs(_uid(), provider=provider, limit=limit)})

    @bp.route("/api/library/sync/runs/<int:run_id>", methods=["GET"])
    @login_required
    def get_sync_run(run_id: int):
        if sync_service is None:
            return jsonify({"error": "sync_not_configured"}), 503
        row = sync_service.get_run(_uid(), run_id)
        if not row:
            return jsonify({"error": "not_found"}), 404
        return jsonify(row)

    @bp.route("/api/library/health", methods=["GET"])
    @login_required
    def library_health():
        from .health import build_library_health

        project_id_raw = request.args.get("project_id")
        project_id = None
        if project_id_raw not in (None, ""):
            try:
                project_id = int(project_id_raw)
            except (TypeError, ValueError):
                project_id = None
        db = SessionLocal()
        try:
            return jsonify(
                build_library_health(
                    db,
                    UserFile,
                    select_fn,
                    _uid(),
                    project_id=project_id,
                    LibrarySyncRun=LibrarySyncRun,
                    LibraryConnection=LibraryConnection,
                )
            )
        finally:
            db.close()

    @bp.route("/api/library/duplicates", methods=["GET"])
    @login_required
    def library_duplicates():
        from .health import find_duplicate_groups

        project_id_raw = request.args.get("project_id")
        project_id = None
        if project_id_raw not in (None, ""):
            try:
                project_id = int(project_id_raw)
            except (TypeError, ValueError):
                project_id = None
        try:
            limit = max(1, min(100, int(request.args.get("limit", 50))))
        except (TypeError, ValueError):
            limit = 50
        db = SessionLocal()
        try:
            groups = find_duplicate_groups(
                db,
                UserFile,
                select_fn,
                _uid(),
                project_id=project_id,
                limit_groups=limit,
            )
            return jsonify({"items": groups, "count": len(groups)})
        finally:
            db.close()

    @bp.route("/api/library/duplicates/merge", methods=["POST"])
    @login_required
    @_rate("30 per hour")
    def library_duplicates_merge():
        from .health import merge_duplicate_files

        body = request.get_json(silent=True) or {}
        try:
            keep_id = int(body.get("keep_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "keep_id_required"}), 400
        raw_ids = body.get("merge_ids") or body.get("file_ids") or []
        if not isinstance(raw_ids, list) or not raw_ids:
            return jsonify({"error": "merge_ids_required"}), 400
        try:
            merge_ids = [int(x) for x in raw_ids]
        except (TypeError, ValueError):
            return jsonify({"error": "invalid_merge_ids"}), 400
        delete_merged = str(body.get("delete_merged", "true")).lower() not in {
            "0",
            "false",
            "no",
        }
        db = SessionLocal()
        try:
            result = merge_duplicate_files(
                db,
                UserFile,
                _uid(),
                keep_id=keep_id,
                merge_ids=merge_ids,
                delete_merged=delete_merged,
            )
            if result.get("error"):
                return jsonify(result), 404
            keep = db.get(UserFile, keep_id)
            if file_to_dict and keep:
                result["file"] = file_to_dict(keep)
            return jsonify(result)
        except Exception as exc:
            db.rollback()
            return jsonify({"error": "merge_failed", "detail": str(exc)[:200]}), 500
        finally:
            db.close()

    @bp.route("/api/library/files/<int:fid>/attach", methods=["POST"])
    @login_required
    @_rate("30 per hour")
    def attach_pdf_to_stub(fid: int):
        """Attach a PDF to a metadata-only library stub → Research Asset.

        Leaves bibliographic fields intact; stores bytes; enqueues ``import``
        (extract + chunk + phase1), not bare phase1_analysis.
        """
        import os
        import uuid

        if storage is None or not upload_dir:
            return jsonify({"error": "storage_not_configured"}), 503

        f = request.files.get("file")
        if not f or not f.filename:
            return jsonify({"error": "no_file"}), 400

        from backend.upload.validation import (
            ValidationError as UploadValidationError,
            kind_for_extension,
            validate_extension,
            validate_upload_path,
        )

        name = f.filename
        try:
            ext = validate_extension(name, allowed=allowed_extensions or {".pdf", ".PDF"})
        except UploadValidationError as e:
            return jsonify({"error": e.code, "detail": e.message}), 400
        if ext.lower() != ".pdf":
            return jsonify({"error": "pdf_required", "detail": "Attach a PDF to analyse this paper."}), 400

        db = SessionLocal()
        try:
            uf = db.get(UserFile, fid)
            if not uf or uf.user_id != _uid():
                return jsonify({"error": "not_found"}), 404
            if (uf.path or "").strip() and int(uf.size or 0) > 0:
                return jsonify(
                    {
                        "error": "already_has_pdf",
                        "detail": "This library entry already has a PDF attached.",
                        "file": file_to_dict(uf) if file_to_dict else {"id": uf.id},
                    }
                ), 409

            disk_name = uuid.uuid4().hex + ext
            path = os.path.join(upload_dir, disk_name)
            f.save(path)
            size = os.path.getsize(path)
            try:
                _, mime = validate_upload_path(
                    path,
                    name,
                    allowed=allowed_extensions or {".pdf"},
                    size_bytes=size,
                    max_mb=max_file_mb or 50,
                )
            except UploadValidationError as e:
                try:
                    os.remove(path)
                except OSError:
                    pass
                return jsonify({"error": e.code, "detail": e.message}), 400

            checksum = storage.sha256_file(path)
            try:
                storage.upload(disk_name, path)
            except Exception:
                try:
                    os.remove(path)
                except OSError:
                    pass
                return jsonify({"error": "storage_unavailable"}), 502
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass

            uf.path = disk_name
            uf.size = size
            uf.mime = mime or "application/pdf"
            uf.kind = kind_for_extension(ext) or "document"
            uf.checksum_sha256 = checksum
            uf.meta_status = "pending"
            if not (uf.name or "").strip() or uf.name == uf.title:
                uf.name = name[:300]
            db.flush()
            queued = False
            if _enqueue_after_attach:
                try:
                    _enqueue_after_attach(db, _uid(), uf.id)
                    queued = True
                except Exception:
                    queued = False
            db.commit()
            db.refresh(uf)
            return jsonify(
                {
                    "ok": True,
                    "file": file_to_dict(uf) if file_to_dict else {"id": uf.id},
                    "queued": queued,
                }
            ), 201
        except Exception as exc:
            db.rollback()
            return jsonify({"error": "attach_failed", "detail": str(exc)[:200]}), 500
        finally:
            db.close()

    def _token_kwargs_for_row(db, row, provider: str) -> dict:
        if provider == "zotero":
            toks = _oauth_plain(row)
            return {
                "access_token": toks["access_token"],
                "access_secret": toks["access_secret"],
                "external_user_id": row.external_user_id,
            }
        toks = _oauth_plain(row)
        token = (toks["access_token"] or "").strip()
        if token:
            return {"access_token": token}
        refresh = (toks["refresh_token"] or "").strip()
        if not refresh:
            raise RuntimeError("mendeley_not_connected")
        refreshed = mendeley_mod.refresh_access_token(refresh)
        _store_oauth(
            row,
            access_token=refreshed.get("access_token") or "",
            refresh_token=refreshed.get("refresh_token") or refresh,
        )
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"access_token": _oauth_plain(row)["access_token"] or ""}

    def _run_provider_pull_pdfs(provider: str, *, file_ids=None, limit=20):
        from .file_pull import pull_pdfs_for_provider

        if storage is None or not upload_dir:
            return jsonify({"error": "storage_not_configured"}), 503
        db = SessionLocal()
        try:
            row = _get_connection(db, _uid(), provider)
            if not row:
                return jsonify({"error": "not_connected"}), 400
            try:
                token_kwargs = _token_kwargs_for_row(db, row, provider)
            except Exception as exc:
                return jsonify({"error": "auth_failed", "detail": str(exc)[:200]}), 401
            result = pull_pdfs_for_provider(
                db=db,
                UserFile=UserFile,
                select_fn=select_fn,
                provider=provider,
                user_id=_uid(),
                token_kwargs=token_kwargs,
                storage=storage,
                upload_dir=upload_dir,
                enqueue_import=_enqueue_after_attach,
                file_ids=file_ids,
                limit=limit,
                max_file_mb=max_file_mb or 50,
            )
            db.commit()
            return jsonify(result), 200 if result.get("ok") else 400
        except Exception as exc:
            db.rollback()
            return jsonify({"error": "pull_failed", "detail": str(exc)[:200]}), 500
        finally:
            db.close()

    @bp.route("/api/library/zotero/pull-pdfs", methods=["POST"])
    @login_required
    @_rate("20 per hour")
    def zotero_pull_pdfs():
        data = request.get_json(silent=True) or {}
        raw_ids = data.get("file_ids") or []
        file_ids = []
        for x in raw_ids if isinstance(raw_ids, list) else []:
            try:
                file_ids.append(int(x))
            except (TypeError, ValueError):
                continue
        limit = int(data.get("limit") or (len(file_ids) if file_ids else 20))
        return _run_provider_pull_pdfs("zotero", file_ids=file_ids or None, limit=limit)

    @bp.route("/api/library/mendeley/pull-pdfs", methods=["POST"])
    @login_required
    @_rate("20 per hour")
    def mendeley_pull_pdfs():
        data = request.get_json(silent=True) or {}
        raw_ids = data.get("file_ids") or []
        file_ids = []
        for x in raw_ids if isinstance(raw_ids, list) else []:
            try:
                file_ids.append(int(x))
            except (TypeError, ValueError):
                continue
        limit = int(data.get("limit") or (len(file_ids) if file_ids else 20))
        return _run_provider_pull_pdfs("mendeley", file_ids=file_ids or None, limit=limit)

    @bp.route("/api/library/files/<int:fid>/pull-pdf", methods=["POST"])
    @login_required
    @_rate("30 per hour")
    def pull_pdf_for_file(fid: int):
        """Pull PDF from the connected ref-mgr for one metadata stub."""
        db = SessionLocal()
        try:
            uf = db.get(UserFile, fid)
            if not uf or uf.user_id != _uid():
                return jsonify({"error": "not_found"}), 404
            provider = (getattr(uf, "external_provider", None) or "").strip().lower()
            if provider not in {"zotero", "mendeley"}:
                return (
                    jsonify(
                        {
                            "error": "not_ref_mgr",
                            "detail": "This paper is not linked to Zotero or Mendeley.",
                        }
                    ),
                    400,
                )
            if not (getattr(uf, "external_item_id", None) or "").strip():
                return jsonify({"error": "missing_external_id"}), 400
        finally:
            db.close()
        return _run_provider_pull_pdfs(provider, file_ids=[fid], limit=1)

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

    # ── Collections ─────────────────────────────────────────────────────
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
