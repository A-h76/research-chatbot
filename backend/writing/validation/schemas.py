from __future__ import annotations

from dataclasses import dataclass

from backend.writing.api.errors import ErrorCode, WritingDomainError

MAX_TITLE = 300
MAX_CONTENT = 200_000


@dataclass(frozen=True)
class DocumentMutation:
    title: str
    content: str


def normalize_document_mutation(title: str | None, content: str | None) -> DocumentMutation:
    t = (title or "").strip()
    c = content or ""
    if len(t) > MAX_TITLE:
        raise WritingDomainError(ErrorCode.VALIDATION, f"title exceeds {MAX_TITLE} chars")
    if len(c) > MAX_CONTENT:
        raise WritingDomainError(ErrorCode.VALIDATION, f"content exceeds {MAX_CONTENT} chars")
    return DocumentMutation(title=t, content=c)

