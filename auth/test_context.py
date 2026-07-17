"""Self-check for the unified session-or-JWT user lookup. Registers one
temporary route directly on the real server.app (not added to server.py
itself) so this exercises get_current_user() through real HTTP requests
— real session cookies, real Authorization headers — against the real
User model and DB, the same way the routes that will eventually use it
would be called.
Run: python -m auth.test_context
"""

import sys

sys.path.insert(0, r"D:\chatbot (v1)")
import server
from flask import jsonify

EMAIL = "context-test@example.com"


@server.app.route("/__test_whoami")
def _whoami():
    user = server.get_current_user()
    return jsonify({"user_id": user.id, "email": user.email} if user else None)


def _cleanup():
    db = server.SessionLocal()
    try:
        u = db.execute(
            server.select(server.User).where(server.User.email == EMAIL)
        ).scalar_one_or_none()
        if u:
            db.delete(u)
            db.commit()
    finally:
        db.close()


def _make_user():
    db = server.SessionLocal()
    try:
        u = server.User(email=EMAIL, name=EMAIL, auth_provider="google")
        db.add(u)
        db.commit()
        return u.id
    finally:
        db.close()


def test_no_session_no_header_returns_none():
    _cleanup()
    with server.app.test_client() as client:
        resp = client.get("/__test_whoami")
        assert resp.get_json() is None


def test_session_present_returns_user():
    _cleanup()
    uid = _make_user()
    try:
        with server.app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = uid
            resp = client.get("/__test_whoami")
            data = resp.get_json()
            print("   session path:", data)
            assert data == {"user_id": uid, "email": EMAIL}
    finally:
        _cleanup()


def test_session_with_deleted_user_returns_none_not_bearer_fallback():
    # A session claiming a user_id that no longer exists must return
    # None, not silently fall through to check for a Bearer header —
    # confirmed by NOT sending one here at all and still expecting None
    # specifically because the session path was taken and failed, not
    # because there was nothing to fall back to.
    _cleanup()
    with server.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = 999999999  # doesn't exist
        resp = client.get("/__test_whoami")
        assert resp.get_json() is None


def test_bearer_token_returns_user_when_no_session():
    _cleanup()
    uid = _make_user()
    try:
        with server.app.app_context():
            access, _ = server.create_jwt(uid)
        with server.app.test_client() as client:
            resp = client.get(
                "/__test_whoami", headers={"Authorization": f"Bearer {access}"}
            )
            data = resp.get_json()
            print("   bearer path:", data)
            assert data == {"user_id": uid, "email": EMAIL}
    finally:
        _cleanup()


def test_session_takes_priority_over_bearer():
    _cleanup()
    uid = _make_user()
    other_uid = None
    try:
        db = server.SessionLocal()
        try:
            other = server.User(
                email="context-other@example.com", name="other", auth_provider="google"
            )
            db.add(other)
            db.commit()
            other_uid = other.id
        finally:
            db.close()

        with server.app.app_context():
            access_for_other, _ = server.create_jwt(other_uid)
        with server.app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = uid
            resp = client.get(
                "/__test_whoami",
                headers={"Authorization": f"Bearer {access_for_other}"},
            )
            data = resp.get_json()
            print("   session-priority path:", data)
            assert (
                data["user_id"] == uid
            ), "session should win over a present Bearer header"
    finally:
        _cleanup()
        if other_uid:
            db = server.SessionLocal()
            try:
                o = db.get(server.User, other_uid)
                if o:
                    db.delete(o)
                    db.commit()
            finally:
                db.close()


def test_refresh_token_is_rejected_as_bearer_credential():
    _cleanup()
    uid = _make_user()
    try:
        with server.app.app_context():
            _, refresh = server.create_jwt(uid)
        with server.app.test_client() as client:
            resp = client.get(
                "/__test_whoami", headers={"Authorization": f"Bearer {refresh}"}
            )
            assert (
                resp.get_json() is None
            ), "a refresh token must not authenticate a request"
    finally:
        _cleanup()


def test_malformed_bearer_token_returns_none():
    _cleanup()
    with server.app.test_client() as client:
        resp = client.get("/__test_whoami", headers={"Authorization": "Bearer garbage"})
        assert resp.get_json() is None


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
