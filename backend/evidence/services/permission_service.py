from __future__ import annotations

from backend.evidence.api.errors import ErrorCode, EvidenceDomainError


def require_owned_project(db, Project, *, user_id: int, project_id: int):
    project = db.get(Project, int(project_id))
    if not project or int(project.user_id) != int(user_id):
        raise EvidenceDomainError(ErrorCode.NOT_FOUND, "project_not_found")
    return project


def require_owned_document(db, WritingDocument, *, user_id: int, document_id: int):
    doc = db.get(WritingDocument, int(document_id))
    if not doc or int(doc.user_id) != int(user_id):
        raise EvidenceDomainError(ErrorCode.NOT_FOUND, "document_not_found")
    return doc


def require_owned_file(db, UserFile, *, user_id: int, file_id: int, project_id: int | None = None):
    uf = db.get(UserFile, int(file_id))
    if not uf or int(uf.user_id) != int(user_id):
        raise EvidenceDomainError(ErrorCode.NOT_FOUND, "file_not_found")
    if project_id is not None and uf.project_id is not None and int(uf.project_id) != int(project_id):
        raise EvidenceDomainError(ErrorCode.NOT_FOUND, "file_not_in_project")
    return uf


def require_owned_evidence(db, EvidenceObject, *, user_id: int, evidence_id: int):
    row = db.get(EvidenceObject, int(evidence_id))
    if not row or int(row.user_id) != int(user_id):
        raise EvidenceDomainError(ErrorCode.NOT_FOUND, "evidence_not_found")
    return row
