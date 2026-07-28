from __future__ import annotations

from backend.writing.api.errors import ErrorCode, WritingDomainError


def require_owned_project(db, Project, *, user_id: int, project_id: int):
    project = db.get(Project, int(project_id))
    if not project or int(project.user_id) != int(user_id):
        raise WritingDomainError(ErrorCode.NOT_FOUND, "project_not_found")
    return project


def require_owned_document(db, WritingDocument, *, user_id: int, document_id: int):
    doc = db.get(WritingDocument, int(document_id))
    if not doc or int(doc.user_id) != int(user_id):
        raise WritingDomainError(ErrorCode.NOT_FOUND, "document_not_found")
    return doc

