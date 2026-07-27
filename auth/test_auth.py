"""Self-check for the auth package — no framework, no fixtures.
Uses a minimal standalone Flask app (not server.py — avoids needing a
DB/OAuth/R2 just to test token verification).
Run: python -m auth.test_auth
"""

from datetime import timedelta

from flask import Flask, g, jsonify
from flask_jwt_extended import JWTManager, create_access_token

from auth.decorators import jwt_optional, jwt_required
from auth.jwt_utils import JWTError, create_jwt, decode_jwt


def _make_app():
    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-at-least-32-bytes-long-for-hs256",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
    )
    JWTManager(app)

    @app.route("/protected")
    @jwt_required()
    def protected():
        return jsonify({"current_user": g.current_user})

    @app.route("/optional")
    @jwt_optional
    def optional():
        return jsonify({"current_user": g.current_user})

    return app


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_create_and_decode_round_trip():
    app = _make_app()
    with app.app_context():
        access, refresh = create_jwt(42, additional_claims={"role": "researcher"})
        assert access and refresh and access != refresh

        claims = decode_jwt(access)
        assert claims["sub"] == "42"
        assert claims["role"] == "researcher"
        assert claims["type"] == "access"

        refresh_claims = decode_jwt(refresh)
        assert refresh_claims["type"] == "refresh"


def test_decode_malformed_token_raises_jwt_error():
    app = _make_app()
    with app.app_context():
        try:
            decode_jwt("not.a.real.token")
            assert False, "expected JWTError"
        except JWTError:
            pass


def test_decode_expired_token_raises_jwt_error():
    app = _make_app()
    with app.app_context():
        expired = create_access_token(identity="1", expires_delta=timedelta(seconds=-1))
        try:
            decode_jwt(expired)
            assert False, "expected JWTError"
        except JWTError:
            pass


def test_jwt_required_route_with_valid_token():
    app = _make_app()
    client = app.test_client()
    with app.app_context():
        access, _ = create_jwt(7)
    resp = client.get("/protected", headers=_auth_header(access))
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["current_user"] == "7"


def test_jwt_required_route_with_missing_token():
    app = _make_app()
    client = app.test_client()
    resp = client.get("/protected")
    assert resp.status_code == 401, resp.get_json()


def test_jwt_required_route_with_malformed_token():
    # A token that can't even be parsed into JWT segments gets 422 from
    # flask_jwt_extended, not 401 — it reserves 401 for a well-formed
    # token that fails verification (bad signature, expired). Both are
    # "rejected," so the meaningful assertion is "not 200."
    app = _make_app()
    client = app.test_client()
    resp = client.get("/protected", headers=_auth_header("garbage"))
    assert resp.status_code == 422, resp.get_json()


def test_jwt_required_route_with_expired_token():
    app = _make_app()
    client = app.test_client()
    with app.app_context():
        expired = create_access_token(identity="1", expires_delta=timedelta(seconds=-1))
    resp = client.get("/protected", headers=_auth_header(expired))
    assert resp.status_code == 401, resp.get_json()


def test_jwt_optional_route_with_missing_token():
    app = _make_app()
    client = app.test_client()
    resp = client.get("/optional")
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["current_user"] is None


def test_jwt_optional_route_with_valid_token():
    app = _make_app()
    client = app.test_client()
    with app.app_context():
        access, _ = create_jwt(9)
    resp = client.get("/optional", headers=_auth_header(access))
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["current_user"] == "9"


def test_jwt_optional_route_with_malformed_token_still_rejects():
    # optional=True only excuses a MISSING token — a present-but-invalid
    # one still fails (422 here, same reasoning as the required-route
    # test above), matching flask_jwt_extended's own semantics: a
    # request that tried to authenticate and got it wrong is different
    # from one that didn't try.
    app = _make_app()
    client = app.test_client()
    resp = client.get("/optional", headers=_auth_header("garbage"))
    assert resp.status_code == 422, resp.get_json()


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
