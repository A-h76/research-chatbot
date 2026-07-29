"""Phase 4 security: token crypto, request validation, CSP enforce."""

from __future__ import annotations

from types import SimpleNamespace

from security.headers import apply_security_headers, resolve_csp
from security.request_validation import (
    RequestValidationError,
    parse_json_object,
    reject_unknown_fields,
    require_string,
)
from security.token_crypto import seal_secret, unseal_secret


def test_seal_unseal_round_trip():
    sealed = seal_secret("oauth-token-xyz", secret_key="test-secret-key-32chars!!!!!!!!")
    assert sealed.startswith("enc:v1:")
    assert unseal_secret(sealed, secret_key="test-secret-key-32chars!!!!!!!!") == "oauth-token-xyz"


def test_unseal_legacy_plaintext_passthrough():
    assert unseal_secret("plain-legacy", secret_key="k") == "plain-legacy"


def test_reject_unknown_fields():
    try:
        reject_unknown_fields({"a": 1, "evil": 2}, {"a"})
        assert False, "expected error"
    except RequestValidationError as exc:
        assert exc.code == "unexpected_fields"


def test_require_string_max_len():
    try:
        require_string({"q": "x" * 10}, "q", max_len=5)
        assert False
    except RequestValidationError as exc:
        assert exc.code == "field_too_long"


def test_parse_json_object_rejects_list():
    try:
        parse_json_object([1, 2], allow_empty=False)
        assert False
    except RequestValidationError as exc:
        assert exc.code == "invalid_json"


def test_csp_enforced_in_production_by_default():
    policy, enforce = resolve_csp(is_production=True, environ={})
    assert policy
    assert enforce is True


def test_csp_report_only_rollback_flag():
    policy, enforce = resolve_csp(is_production=True, environ={"CSP_REPORT_ONLY": "1"})
    assert policy
    assert enforce is False


def test_apply_headers_sets_enforcing_csp():
    resp = SimpleNamespace(headers={})
    apply_security_headers(resp, is_production=True, environ={})
    assert "Content-Security-Policy" in resp.headers
    assert "Content-Security-Policy-Report-Only" not in resp.headers
