"""Admin-facing CRUD for the Prompt Engine's prompts/personas, plus a
preview endpoint — session-authenticated (@login_required), not
Bearer-JWT like backend/upload and backend/search: these are internal
authoring/admin surfaces, not a document-centric API for external
clients, and the task's own Security requirement names @login_required
specifically. Mutating routes (create/update) additionally require
admin_required (auth/decorators.py's create_admin_required) — read
routes (list/get/preview) don't, matching how GET /api/ai/prompts
already works today (any logged-in user, no admin gate).

Constructor-injected (SessionLocal, model classes, get_prompt_builder,
the two decorators), never `import server` — same reason as every other
module in backend/: server.py runs as __main__, so a module it reaches
into importing it back re-executes the whole file under a second module
identity and recurses.
"""
import json

from flask import Blueprint, request, jsonify, session


def _prompt_to_dict(row):
    return {
        "id": row.id,
        "name": row.name,
        "version": row.version,
        "template": row.template,
        "is_active": row.is_active,
        "status": row.status,
        "category": row.category,
        "description": row.description,
        "expected_output_type": row.expected_output_type,
        "examples": json.loads(row.examples) if row.examples else [],
        "author_user_id": row.author_user_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _persona_to_dict(row):
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "system_prompt": row.system_prompt,
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def create_prompts_blueprint(
    *, SessionLocal, PromptVersion, Persona, PromptRegistry, PersonaEngine,
    get_prompt_builder, login_required, admin_required,
):
    bp = Blueprint("prompts", __name__)

    # ------------------------------------------------------------ prompts: read
    @bp.route("/api/prompts", methods=["GET"])
    @login_required
    def list_prompts_route():
        db = SessionLocal()
        try:
            rows = PromptRegistry(db).list_prompts()
            category = request.args.get("category")
            status = request.args.get("status")
            if category:
                rows = [r for r in rows if r.category == category]
            if status:
                rows = [r for r in rows if r.status == status]
            return jsonify({"prompts": [_prompt_to_dict(r) for r in rows]})
        finally:
            db.close()

    @bp.route("/api/prompts/<int:prompt_id>", methods=["GET"])
    @login_required
    def get_prompt_route(prompt_id):
        db = SessionLocal()
        try:
            row = db.get(PromptVersion, prompt_id)
            if not row:
                return jsonify({"error": "not_found"}), 404
            return jsonify(_prompt_to_dict(row))
        finally:
            db.close()

    # ------------------------------------------------------------ prompts: write
    @bp.route("/api/prompts", methods=["POST"])
    @login_required
    @admin_required
    def create_prompt_route():
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        template = data.get("template")
        if not name or not template:
            return (
                jsonify({"error": "missing_fields", "message": "name and template are required"}),
                400,
            )

        db = SessionLocal()
        try:
            registry = PromptRegistry(db)
            try:
                row = registry.create_prompt(
                    name, data.get("description", ""), template,
                    status=data.get("status", "draft"),
                    category=data.get("category", ""),
                    examples=data.get("examples"),
                    expected_output_type=data.get("expected_output_type", "text"),
                    author_user_id=session.get("user_id"),
                )
            except ValueError as exc:
                return jsonify({"error": "already_exists", "message": str(exc)}), 409
            return jsonify(_prompt_to_dict(row)), 201
        finally:
            db.close()

    @bp.route("/api/prompts/<int:prompt_id>", methods=["PATCH"])
    @login_required
    @admin_required
    def update_prompt_route(prompt_id):
        data = request.get_json(silent=True) or {}
        db = SessionLocal()
        try:
            row = db.get(PromptVersion, prompt_id)
            if not row:
                return jsonify({"error": "not_found"}), 404

            registry = PromptRegistry(db)
            requested_status = data.get("status")
            try:
                # activate_prompt()/archive_prompt() operate on the
                # *latest* version for this name, not necessarily this
                # exact row — matches their own documented behavior
                # (see prompt_registry.py); PATCHing an older version's
                # status to "active" activates the newest version of
                # that name, not this one specifically.
                if requested_status == "active":
                    row = registry.activate_prompt(row.name)
                elif requested_status == "archived":
                    row = registry.archive_prompt(row.name)
            except ValueError as exc:
                return jsonify({"error": "invalid_state", "message": str(exc)}), 400

            for field in ("description", "category", "expected_output_type"):
                if field in data:
                    setattr(row, field, data[field])
            if "examples" in data:
                row.examples = json.dumps(data["examples"])
            db.commit()
            return jsonify(_prompt_to_dict(row))
        finally:
            db.close()

    @bp.route("/api/prompts/<int:prompt_id>/versions", methods=["POST"])
    @login_required
    @admin_required
    def create_prompt_version_route(prompt_id):
        data = request.get_json(silent=True) or {}
        template = data.get("template")
        if not template:
            return jsonify({"error": "missing_fields", "message": "template is required"}), 400

        db = SessionLocal()
        try:
            existing = db.get(PromptVersion, prompt_id)
            if not existing:
                return jsonify({"error": "not_found"}), 404

            registry = PromptRegistry(db)
            try:
                row = registry.add_version(
                    existing.name, template,
                    is_active=bool(data.get("is_active", False)),
                    status=data.get("status", "draft"),
                    description=data.get("description", ""),
                    category=data.get("category", existing.category),
                    examples=data.get("examples"),
                    expected_output_type=data.get("expected_output_type", existing.expected_output_type),
                    author_user_id=session.get("user_id"),
                )
            except ValueError as exc:
                return jsonify({"error": "invalid_state", "message": str(exc)}), 400
            return jsonify(_prompt_to_dict(row)), 201
        finally:
            db.close()

    # ------------------------------------------------------------ preview
    @bp.route("/api/prompts/preview", methods=["POST"])
    @login_required
    def preview_prompt_route():
        data = request.get_json(silent=True) or {}
        task_name = data.get("task_name")
        if not task_name:
            return jsonify({"error": "missing_fields", "message": "task_name is required"}), 400

        db = SessionLocal()
        try:
            builder = get_prompt_builder(db)
            try:
                result = builder.preview(
                    data.get("user_query", ""), task_name,
                    persona=data.get("persona"),
                    project_id=data.get("project_id"),
                    # Always the logged-in user's own id — never trust a
                    # client-supplied user_id for whose memories get
                    # pulled into the preview.
                    user_id=session.get("user_id"),
                    rag_context=data.get("rag_context"),
                    output_schema=data.get("output_schema"),
                )
            except ValueError as exc:
                return jsonify({"error": "invalid_request", "message": str(exc)}), 400

            return jsonify({
                "system": result.system,
                "persona": result.persona,
                "project_context": result.project_context,
                "memory": result.memory,
                "rag": result.rag,
                "task": result.task,
                "output_schema": result.output_schema,
                "final": result.final,
                "prompt_version_id": result.prompt_version_id,
                "persona_id": result.persona_id,
            })
        finally:
            db.close()

    # ------------------------------------------------------------ personas
    @bp.route("/api/personas", methods=["GET"])
    @login_required
    def list_personas_route():
        db = SessionLocal()
        try:
            rows = PersonaEngine(db, Persona).list_active()
            return jsonify({"personas": [_persona_to_dict(r) for r in rows]})
        finally:
            db.close()

    @bp.route("/api/personas", methods=["POST"])
    @login_required
    @admin_required
    def create_persona_route():
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        system_prompt = data.get("system_prompt")
        if not name or not system_prompt:
            return (
                jsonify({"error": "missing_fields", "message": "name and system_prompt are required"}),
                400,
            )

        db = SessionLocal()
        try:
            try:
                row = PersonaEngine(db, Persona).create(name, data.get("description", ""), system_prompt)
            except ValueError as exc:
                return jsonify({"error": "already_exists", "message": str(exc)}), 409
            return jsonify(_persona_to_dict(row)), 201
        finally:
            db.close()

    return bp
