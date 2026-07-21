"""Bearer-token auth decorators, layered on Flask-JWT-Extended's own
jwt_required()/jwt_required(optional=True) — this module's only job is
attaching g.current_user consistently, not reimplementing verification.

g.current_user is always the same attribute regardless of which
decorator ran (a str user_id, matching create_jwt's identity, or None
for jwt_optional with no/invalid token) — a route shouldn't need to know
which decorator protected it to know where to look.

create_admin_required() below is a different, session-based check (not
JWT) for the Prompt Engine's admin-gated routes (backend/prompts/routes.py)
— a factory, not a plain decorator, because it needs SessionLocal/User
injected (same reason as every other module here: server.py runs as
__main__, so this can't `import server` to get them). Uses flask.session
directly rather than needing anything else injected — session is a
request-scoped global proxy, not a real object that needs construction."""

from functools import wraps

from flask import g, session, jsonify
from flask_jwt_extended import jwt_required as _jwt_required, get_jwt_identity


def jwt_required():
    """Verifies the Authorization: Bearer <token> header; aborts with
    401 (via flask_jwt_extended's own error handlers) if missing,
    malformed, or expired. Sets g.current_user on success."""

    def decorator(fn):
        @_jwt_required()
        @wraps(fn)
        def wrapper(*args, **kwargs):
            g.current_user = get_jwt_identity()
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def jwt_optional(fn):
    """Same header check, but never aborts on a missing token — only on
    a present-but-invalid one (expired/malformed/wrong type), matching
    flask_jwt_extended's own optional=True semantics. g.current_user is
    None when no token was supplied."""

    @_jwt_required(optional=True)
    @wraps(fn)
    def wrapper(*args, **kwargs):
        g.current_user = get_jwt_identity()  # None if no token given
        return fn(*args, **kwargs)

    return wrapper


def create_admin_required(SessionLocal, User):
    """Returns an admin_required decorator for stacking under
    @login_required: `@login_required` then `@admin_required`, in that
    order (outer to inner) — @login_required already turns "no session"
    into a 401 before this ever runs, so this only has to check the role.
    Still checks session itself too (defense in depth, near-zero cost) in
    case a route ever uses this one without @login_required by mistake."""

    def admin_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = session.get("user_id")
            if user_id is None:
                return jsonify({"error": "not_authenticated"}), 401
            db = SessionLocal()
            try:
                user = db.get(User, user_id)
                is_admin = bool(user and user.is_admin)
            finally:
                db.close()
            if not is_admin:
                return jsonify({"error": "forbidden", "message": "Admin access required"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return admin_required
