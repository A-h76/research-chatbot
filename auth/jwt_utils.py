"""JWT issuing/verification — thin wrapper over Flask-JWT-Extended so
callers depend on this module's contract (one exception type, one
function shape) instead of flask_jwt_extended's or PyJWT's own
exception hierarchy directly.

Requires an active Flask app/request context (JWTManager(app) configured
in server.py) — these functions read app.config at call time via
flask_jwt_extended, they don't take an app reference themselves.

Session binding (Phase 2 / F2.1): every token carries claim ``sv`` =
User.session_version at mint time. After logout-all / password reset
(session_version bump), tokens with a stale ``sv`` are rejected.
"""

from flask_jwt_extended import create_access_token, create_refresh_token, decode_token


class JWTError(Exception):
    """Raised by decode_jwt() for anything wrong with a token — expired,
    malformed, wrong signature, wrong type. Callers only ever need to
    catch this one type, not flask_jwt_extended's or PyJWT's."""


# Claim name for User.session_version binding (logout-all / revoke).
SESSION_VERSION_CLAIM = "sv"


def create_jwt(user_id, additional_claims=None, *, session_version=0):
    """Returns (access_token, refresh_token) for `user_id`.

    Always embeds ``sv`` (session_version) so revoke_all_sessions /
    password reset invalidate JWTs as well as cookie sessions.
    """
    identity = str(user_id)
    claims = dict(additional_claims or {})
    claims[SESSION_VERSION_CLAIM] = int(session_version or 0)
    access = create_access_token(identity=identity, additional_claims=claims)
    refresh = create_refresh_token(identity=identity, additional_claims=claims)
    return access, refresh


def decode_jwt(token):
    """Returns the decoded claims dict, or raises JWTError."""
    try:
        return decode_token(token)
    except Exception as e:
        raise JWTError(str(e)) from e


def session_version_matches(claims: dict, current_version: int) -> bool:
    """True when token ``sv`` equals the user's current session_version."""
    if not isinstance(claims, dict) or SESSION_VERSION_CLAIM not in claims:
        return False
    try:
        return int(claims[SESSION_VERSION_CLAIM]) == int(current_version or 0)
    except (TypeError, ValueError):
        return False
