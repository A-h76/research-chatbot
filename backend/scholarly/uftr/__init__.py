"""Universal Full-Text Resolution (UFTR) — platform service v1.0

Status: Production Ready

===========================================================================
INTEGRATION BOUNDARY (binding)
---------------------------------------------------------------------------
Future connectors that start from a paper reference / DOI / OA URL must NOT
implement PDF fetch logic. Call:

    from backend.scholarly.uftr import resolve_and_attach
    resolve_and_attach(db, user_file, storage=..., upload_dir=...,
                       enqueue_import=..., user_id=..., work=optional_hints)

If you already hold PDF bytes (upload, Drive, manual attach), skip UFTR and
use apply_pdf_bytes_to_stub → enqueue import (Golden Rule attach path).
===========================================================================

Architecture: Resolver Chain discovers candidates; Validator decides FOUND
vs failure. Attach + enqueue stay on the shared import pipeline.

Outcomes:
  FOUND | NO_OPEN_ACCESS | PUBLISHER_PAYWALL | BOT_PROTECTION
  | INVALID_RESPONSE | NETWORK_ERROR | TIMEOUT

Contract: docs/contracts/uftr-contract.md
ADR:      docs/adr/0015-universal-full-text-resolution-v1.md
"""

from __future__ import annotations

UFTR_VERSION = "1.0"
UFTR_STATUS = "production_ready"

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
    "UFTR_VERSION",
    "UFTR_STATUS",
    # Primary platform API
    "resolve_and_attach",
    # Supporting (diagnostics / UI / state — not “how to fetch a PDF”)
    "USER_REASON",
    "FullTextOutcome",
    "ResolutionAttempt",
    "ResolutionResult",
    "content_kind_for_bytes",
    "resolve_full_text",
    "resolve_from_user_file",
    "FULLTEXT_NEEDED_OUTCOMES",
    "apply_resolution_to_file",
    "fulltext_payload",
    "lifecycle_label",
    "parse_fulltext_json",
    "record_manual_attach",
    "should_auto_retry",
]
