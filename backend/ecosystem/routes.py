"""Integrations catalog HTTP facade (factory — never import server)."""

from __future__ import annotations

from flask import Blueprint, jsonify, session

from backend.ecosystem.catalog import build_catalog, public_catalog


def create_integrations_catalog_blueprint(
    *,
    SessionLocal,
    UserFile,
    LibraryConnection,
    LibrarySyncRun,
    select_fn,
    login_required,
):
    bp = Blueprint("integrations_catalog", __name__)

    @bp.route("/api/integrations/catalog", methods=["GET"])
    @login_required
    def integrations_catalog():
        uid = session.get("user_id")
        google_connected = bool(session.get("user_id"))  # signed-in session
        # Prefer explicit google flag when present
        if session.get("auth_provider") == "google":
            google_connected = True
        data = build_catalog(
            user_id=int(uid) if uid is not None else None,
            SessionLocal=SessionLocal,
            LibraryConnection=LibraryConnection,
            LibrarySyncRun=LibrarySyncRun,
            UserFile=UserFile,
            select_fn=select_fn,
            google_connected=google_connected,
        )
        return jsonify(data)

    @bp.route("/api/integrations/catalog/public", methods=["GET"])
    def integrations_catalog_public():
        """Marketing / landing — Live vs Coming Soon only (no user state)."""
        return jsonify(public_catalog())

    return bp
