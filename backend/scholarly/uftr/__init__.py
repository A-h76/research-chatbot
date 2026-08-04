"""Universal Full-Text Resolution (UFTR) — Product Hardening #1.

Resolver Chain discovers candidate URLs; Validator decides FOUND vs failure
outcomes. After FOUND, callers attach via apply_pdf_bytes_to_stub (Golden Rule).

Outcomes (engineering):
  FOUND | NO_OPEN_ACCESS | PUBLISHER_PAYWALL | BOT_PROTECTION
  | INVALID_RESPONSE | NETWORK_ERROR | TIMEOUT
"""

from __future__ import annotations

from backend.scholarly.uftr.outcomes import (
    USER_REASON,
    FullTextOutcome,
    ResolutionAttempt,
    ResolutionResult,
    content_kind_for_bytes,
)
from backend.scholarly.uftr.resolve import (
    resolve_and_attach,
    resolve_from_user_file,
    resolve_full_text,
)
from backend.scholarly.uftr.state import (
    FULLTEXT_NEEDED_OUTCOMES,
    apply_resolution_to_file,
    fulltext_payload,
    lifecycle_label,
    parse_fulltext_json,
    record_manual_attach,
    should_auto_retry,
)

__all__ = [
    "USER_REASON",
    "FullTextOutcome",
    "ResolutionAttempt",
    "ResolutionResult",
    "content_kind_for_bytes",
    "resolve_full_text",
    "resolve_from_user_file",
    "resolve_and_attach",
    "FULLTEXT_NEEDED_OUTCOMES",
    "apply_resolution_to_file",
    "fulltext_payload",
    "lifecycle_label",
    "parse_fulltext_json",
    "record_manual_attach",
    "should_auto_retry",
]
