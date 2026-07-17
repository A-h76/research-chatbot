"""JWT issuing/verification — thin wrapper over Flask-JWT-Extended so
callers depend on this module's contract (one exception type, one
function shape) instead of flask_jwt_extended's or PyJWT's own
exception hierarchy directly.

Requires an active Flask app/request context (JWTManager(app) configured
in server.py) — these functions read app.config at call time via
flask_jwt_extended, they don't take an app reference themselves.
"""

from flask_jwt_extended import create_access_token, create_refresh_token, decode_token


class JWTError(Exception):
    """Raised by decode_jwt() for anything wrong with a token — expired,
    malformed, wrong signature, wrong type. Callers only ever need to
    catch this one type, not flask_jwt_extended's or PyJWT's."""


def create_jwt(user_id, additional_claims=None):
    """Returns (access_token, refresh_token) for `user_id` — the same
    User.id the rest of this app's session-based login already uses, so
    a JWT-authenticated request and a session-authenticated request
    refer to the same identity space. Expiry comes from JWT_ACCESS_
    TOKEN_EXPIRES / JWT_REFRESH_TOKEN_EXPIRES in app.config, set once in
    server.py, not per call."""
    identity = str(user_id)
    access = create_access_token(identity=identity, additional_claims=additional_claims)
    refresh = create_refresh_token(
        identity=identity, additional_claims=additional_claims
    )
    return access, refresh


def decode_jwt(token):
    """Returns the decoded claims dict, or raises JWTError."""
    try:
        return decode_token(token)
    except Exception as e:
        raise JWTError(str(e)) from e
