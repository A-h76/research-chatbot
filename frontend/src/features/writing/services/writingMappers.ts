import type { WritingDocument, WritingDocumentVersion } from "@/types/api";
import type { WritingDocumentView, WritingVersionView } from "../types/writing";

export function toWritingDocumentView(dto: WritingDocument): WritingDocumentView {
  return {
    id: dto.id,
    projectId: dto.project_id,
    title: dto.title,
    content: dto.content,
    state: dto.status,
    currentVersion: dto.current_version,
    updatedAt: dto.updated_at,
  };
}

export function toWritingVersionView(dto: WritingDocumentVersion): WritingVersionView {
  return {
    id: dto.id,
    documentId: dto.document_id,
    versionNo: dto.version_no,
    source: dto.source,
    createdAt: dto.created_at,
  };
}

