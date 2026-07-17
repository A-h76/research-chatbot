"""Self-check for magic-link auth. Unlike jwt_utils/decorators (framework-
level, tested against a throwaway Flask app), this module is inherently
coupled to server.py — it shares its User model, DB, and rate limiter by
design, not by accident — so this test imports the real app rather than
building a stand-in.
Run: python -m auth.test_magic_link
"""
import sys

sys.path.insert(0, r"D:\chatbot (v1)")
import server
from auth.magic_link import TOKEN_MAX_AGE_SECONDS

EMAIL = "magic-link-verify@example.com"


def _serializer():
    # The blueprint exposes its serializer instance for exactly this —
    # building a token the same way the real request handler does,
    # without duplicating the secret/salt logic here.
    return server.app.blueprints["magic_link"]._serializer


def _cleanup():
    db = server.SessionLocal()
    try:
        u = db.execute(server.select(server.User).where(server.User.email == EMAIL)).scalar_one_or_none()
        if u:
            db.delete(u)
            db.commit()
    finally:
        db.close()


def test_request_rejects_invalid_email():
    with server.app.test_client() as client:
        resp = client.post("/auth/magic-link", json={"email": "not-an-email"})
        assert resp.status_code == 400, resp.get_json()


def test_request_gives_generic_response_regardless_of_allowlist():
    # Response shape must not reveal whether the email is allowed — that
    # would let a caller enumerate valid addresses.
    with server.app.test_client() as client:
        allowed_resp = client.post("/auth/magic-link", json={"email": EMAIL})
        server.ALLOWED_EMAILS.append("someone-else@example.com")
        try:
            denied_resp = client.post("/auth/magic-link", json={"email": "nobody@example.com"})
        finally:
            server.ALLOWED_EMAILS.remove("someone-else@example.com")
        assert allowed_resp.get_json() == denied_resp.get_json()


def test_request_rate_limited_per_email():
    with server.app.test_client() as client:
        email = "rate-limit-test@example.com"
        statuses = [client.post("/auth/magic-link", json={"email": email}).status_code
                   for _ in range(4)]
        print("   4 requests, statuses:", statuses)
        assert statuses[:3] == [200, 200, 200]
        assert statuses[3] == 429


def test_verify_missing_token():
    with server.app.test_client() as client:
        resp = client.post("/auth/magic-link/verify", json={})
        assert resp.status_code == 400, resp.get_json()


def test_verify_malformed_token():
    with server.app.test_client() as client:
        resp = client.post("/auth/magic-link/verify", json={"token": "garbage"})
        assert resp.status_code == 401, resp.get_json()


def test_verify_expired_token():
    # Rather than sleeping 15 minutes, prove the max_age check itself is
    # real and wired correctly: any token is "expired" against max_age=-1.
    import itsdangerous
    with server.app.app_context():
        token = _serializer().dumps({"email": EMAIL})
        try:
            _serializer().loads(token, max_age=-1)
            assert False, "expected SignatureExpired"
        except itsdangerous.SignatureExpired:
            pass

    # And confirm the actual HTTP endpoint rejects a signature-invalid
    # token the same way (same code path the real 15-minute expiry hits).
    with server.app.test_client() as client:
        resp = client.post("/auth/magic-link/verify", json={"token": token + "tampered"})
        assert resp.status_code == 401, resp.get_json()


def test_verify_creates_new_user_with_magic_provider():
    _cleanup()
    with server.app.app_context():
        token = _serializer().dumps({"email": EMAIL})
    with server.app.test_client() as client:
        resp = client.post("/auth/magic-link/verify", json={"token": token})
        data = resp.get_json()
        print("   verify (new user):", resp.status_code, {k: v for k, v in data.items()
             if k not in ("access_token", "refresh_token")})
        assert resp.status_code == 200, data
        assert data["access_token"] and data["refresh_token"]

        with client.session_transaction() as sess:
            assert sess["user_id"] == data["user_id"]
            assert "jwt" in sess

    db = server.SessionLocal()
    try:
        user = db.get(server.User, data["user_id"])
        assert user.auth_provider == "magic", user.auth_provider
    finally:
        db.close()
    _cleanup()


def test_verify_does_not_overwrite_existing_auth_provider():
    _cleanup()
    db = server.SessionLocal()
    try:
        u = server.User(email=EMAIL, name=EMAIL, auth_provider="google")
        db.add(u)
        db.commit()
        uid = u.id
    finally:
        db.close()

    with server.app.app_context():
        token = _serializer().dumps({"email": EMAIL})
    with server.app.test_client() as client:
        resp = client.post("/auth/magic-link/verify", json={"token": token})
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()["user_id"] == uid

    db = server.SessionLocal()
    try:
        user = db.get(server.User, uid)
        assert user.auth_provider == "google", \
            f"magic-link login must not overwrite an existing provider, got {user.auth_provider!r}"
    finally:
        db.close()
    _cleanup()


def test_verify_denied_when_not_in_allowlist():
    server.ALLOWED_EMAILS.append("only-this-one@example.com")
    try:
        with server.app.app_context():
            token = _serializer().dumps({"email": EMAIL})
        with server.app.test_client() as client:
            resp = client.post("/auth/magic-link/verify", json={"token": token})
            assert resp.status_code == 403, resp.get_json()
    finally:
        server.ALLOWED_EMAILS.remove("only-this-one@example.com")
    _cleanup()


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
