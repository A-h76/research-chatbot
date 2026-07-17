"""Bearer-token auth decorators, layered on Flask-JWT-Extended's own
jwt_required()/jwt_required(optional=True) — this module's only job is
attaching g.current_user consistently, not reimplementing verification.

g.current_user is always the same attribute regardless of which
decorator ran (a str user_id, matching create_jwt's identity, or None
for jwt_optional with no/invalid token) — a route shouldn't need to know
which decorator protected it to know where to look."""

from functools import wraps

from flask import g
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
