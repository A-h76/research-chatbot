"""Shared JSON request validation (Phase 4).

High-risk write endpoints use this instead of ad-hoc get_json() checks.
Does not rewrite every route — migrate callers intentionally.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping


class RequestValidationError(Exception):
    """Raised when a request body fails schema checks."""

    def __init__(self, code: str, message: str, *, http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status

    def to_response(self):
        from flask import jsonify

        return jsonify({"error": self.code, "message": self.message}), self.http_status


def parse_json_object(raw: Any, *, allow_empty: bool = True) -> dict[str, Any]:
    """Require a JSON object (dict). ``None`` → {} when allow_empty."""
    if raw is None:
        if allow_empty:
            return {}
        raise RequestValidationError("invalid_json", "JSON body required")
    if not isinstance(raw, dict):
        raise RequestValidationError("invalid_json", "JSON body must be an object")
    return raw


def reject_unknown_fields(data: Mapping[str, Any], allowed: Iterable[str]) -> None:
    allowed_set = set(allowed)
    unknown = sorted(k for k in data.keys() if k not in allowed_set)
    if unknown:
        raise RequestValidationError(
            "unexpected_fields",
            f"Unexpected fields: {', '.join(unknown)}",
        )


def require_string(
    data: Mapping[str, Any],
    key: str,
    *,
    max_len: int,
    min_len: int = 0,
    required: bool = True,
    strip: bool = True,
) -> str:
    if key not in data or data[key] is None:
        if required:
            raise RequestValidationError("missing_field", f"Missing field: {key}")
        return ""
    val = data[key]
    if not isinstance(val, str):
        raise RequestValidationError("invalid_type", f"{key} must be a string")
    if strip:
        val = val.strip()
    if required and not val:
        raise RequestValidationError("missing_field", f"Missing field: {key}")
    if min_len and len(val) < min_len:
        raise RequestValidationError("invalid_field", f"{key} too short")
    if len(val) > max_len:
        raise RequestValidationError("field_too_long", f"{key} exceeds {max_len} characters")
    return val


def optional_int(
    data: Mapping[str, Any],
    key: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int | None:
    if key not in data or data[key] is None or data[key] == "":
        return None
    try:
        n = int(data[key])
    except (TypeError, ValueError):
        raise RequestValidationError("invalid_type", f"{key} must be an integer") from None
    if minimum is not None and n < minimum:
        raise RequestValidationError("invalid_field", f"{key} below minimum {minimum}")
    if maximum is not None and n > maximum:
        raise RequestValidationError("invalid_field", f"{key} above maximum {maximum}")
    return n
