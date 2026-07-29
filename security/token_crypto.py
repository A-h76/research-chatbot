"""Seal/unseal secrets at rest (library OAuth tokens).

Uses itsdangerous (already a Flask dependency). Values are prefixed
``enc:v1:`` so plaintext rows written before Phase 4 still decrypt as
themselves (transparent migration on next connect/refresh).
"""

from __future__ import annotations

from itsdangerous import BadSignature, URLSafeSerializer

_PREFIX = "enc:v1:"
_SALT = "dhund-library-oauth-v1"


def _serializer(secret_key: str) -> URLSafeSerializer:
    return URLSafeSerializer(secret_key or "insecure-dev-only", salt=_SALT)


def seal_secret(plain: str | None, *, secret_key: str) -> str:
    """Encrypt a token for DB storage. Empty stays empty."""
    text = (plain or "").strip()
    if not text:
        return ""
    if text.startswith(_PREFIX):
        return text  # already sealed
    return _PREFIX + _serializer(secret_key).dumps(text)


def unseal_secret(stored: str | None, *, secret_key: str) -> str:
    """Decrypt a stored token. Legacy plaintext returned as-is."""
    text = (stored or "").strip()
    if not text:
        return ""
    if not text.startswith(_PREFIX):
        return text
    try:
        return str(_serializer(secret_key).loads(text[len(_PREFIX) :]))
    except (BadSignature, TypeError, ValueError):
        return ""
