"""Unified user lookup — session first, Bearer JWT second, None if
neither. Built as a factory (create_get_current_user), not via `import
server`: server.py runs as __main__ (`python server.py`), so a module it
reaches into trying `import server` back would import the *file* a
second time under a separate module identity and re-execute the whole
thing — see auth/magic_link.py's module docstring for the full
explanation of the same issue, hit and fixed there first.
"""
from flask import session, request

from .jwt_utils import decode_jwt, JWTError


def create_get_current_user(SessionLocal, User):
    """Returns a get_current_user() function bound to this app's actual
    SessionLocal/User. The returned User (or None) is a detached ORM
    object — safe to read simple columns off afterward, since
    SessionLocal is configured with expire_on_commit=False; don't rely
    on it for lazy-loaded relationships, re-query with a fresh session
    for those."""

    def _load_user(user_id):
        db = SessionLocal()
        try:
            return db.get(User, user_id)
        finally:
            db.close()

    def get_current_user():
        # 1. Session — set by Google OAuth, dev-login, and magic-link
        # alike (all three write the same session["user_id"]), so this
        # one check covers all of them. A session claiming a user_id
        # that no longer exists (deleted account) returns None here and
        # does NOT fall through to the Bearer check below — the caller
        # did present a session, just an invalid one.
        user_id = session.get("user_id")
        if user_id:
            return _load_user(user_id)

        # 2. Bearer JWT
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
            try:
                claims = decode_jwt(token)
            except JWTError:
                return None
            if claims.get("type") != "access":
                return None   # a refresh token must never authenticate a request
            try:
                user_id = int(claims.get("sub"))
            except (TypeError, ValueError):
                return None
            return _load_user(user_id)

        return None

    return get_current_user
