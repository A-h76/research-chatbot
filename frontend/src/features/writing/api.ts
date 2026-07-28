import { api } from "@/lib/apiClient";
import type {
  WritingAction,
  WritingDocument,
  WritingDocumentListResponse,
  WritingDocumentVersionListResponse,
  WritingResponse,
} from "@/types/api";

export const writingApi = {
  transform: (action: WritingAction, text: string) =>
    api.post<WritingResponse>("/api/writing", { action, text }),

  listDocuments: (
    projectId: number,
    opts?: { status?: "draft" | "active" | "archived" | "deleted"; includeArchived?: boolean; includeDeleted?: boolean },
  ) => {
    const p = new URLSearchParams({ project_id: String(projectId) });
    if (opts?.status) p.set("status", opts.status);
    if (opts?.includeArchived) p.set("include_archived", "1");
    if (opts?.includeDeleted) p.set("include_deleted", "1");
    return api.get<WritingDocumentListResponse>(`/api/writing/documents?${p.toString()}`);
  },

  createDocument: (body: {
    title?: string;
    content?: string;
    project_id?: number | null;
    editor_kind?: "markdown" | "richtext";
  }) => api.post<WritingDocument>("/api/writing/documents", body),

  updateDocument: (
    id: number,
    body: {
      title?: string;
      content?: string;
      project_id?: number | null;
      editor_kind?: "markdown" | "richtext";
      status?: "draft" | "active" | "archived" | "deleted";
      current_version?: number;
    },
  ) => api.patch<WritingDocument>(`/api/writing/documents/${id}`, body),

  autosaveDocument: (
    id: number,
    body: { title: string; content: string; current_version?: number; idempotency_key: string },
  ) =>
    api.post<{ ok: boolean; unchanged: boolean; idempotent_replay: boolean; document: WritingDocument }>(
      `/api/writing/documents/${id}/autosave`,
      body,
    ),

  listVersions: (id: number) =>
    api.get<WritingDocumentVersionListResponse>(
      `/api/writing/documents/${id}/versions`,
    ),

  restoreVersion: (id: number, versionId: number) =>
    api.post<WritingDocument>(`/api/writing/documents/${id}/restore`, {
      version_id: versionId,
    }),

  exportNotes: () =>
    `/api/export/notes`,  // POST — handled inline in the page

  exportAnalysisUrl: (fileId: number, format: "md" | "txt" | "docx") =>
    `/api/export/analysis/${fileId}?format=${format}`,

  exportChatUrl: (convId: number, format: "md" | "txt") =>
    `/api/export/chat/${convId}?format=${format}`,
};
