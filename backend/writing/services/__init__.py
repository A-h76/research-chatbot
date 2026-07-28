"""Writing service-layer scaffolding."""

from .autosave_service import is_idempotent_replay, normalize_idempotency_key
from .container import WritingServices, build_writing_services
from .document_service import normalize_editor_kind, normalize_status_filter
from .permission_service import require_owned_document, require_owned_project
from .version_service import build_version_conflict_payload, next_version_number

__all__ = [
    "WritingServices",
    "build_writing_services",
    "is_idempotent_replay",
    "normalize_idempotency_key",
    "normalize_editor_kind",
    "normalize_status_filter",
    "require_owned_document",
    "require_owned_project",
    "build_version_conflict_payload",
    "next_version_number",
]

