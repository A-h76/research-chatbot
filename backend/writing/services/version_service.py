from __future__ import annotations


def build_version_conflict_payload(current_version: int) -> dict[str, int | str]:
    return {
        "error": "version_conflict",
        "detail": "stale_document_version",
        "current_version": int(current_version or 1),
    }


def next_version_number(current_version: int | None) -> int:
    return int(current_version or 0) + 1

