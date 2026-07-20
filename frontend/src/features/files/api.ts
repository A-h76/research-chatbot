import { api, getBearerToken } from "@/lib/apiClient";
import type { PaperAnalysis, UserFile } from "@/types/api";

export interface UploadResult extends UserFile {
  note?: string | null;
}

// Mirrors backend/upload/validation.py's ALLOWED_EXTENSIONS — that route
// only takes document types, no images.
const JWT_UPLOAD_EXTENSIONS = new Set([".pdf", ".epub", ".docx", ".txt"]);

function isDocumentUpload(filename: string): boolean {
  const dot = filename.lastIndexOf(".");
  return dot !== -1 && JWT_UPLOAD_EXTENSIONS.has(filename.slice(dot).toLowerCase());
}

export interface UploadDocumentResult {
  document_id: number;
  status: string;
  message: string;
}

// The two upload routes have different auth (session vs JWT) and different
// contracts (sync full record vs async job-enqueued placeholder) — callers
// need to know which one they got back.
export type UploadOutcome =
  | { async: false; result: UploadResult }
  | { async: true; result: UploadDocumentResult };

export interface DocumentAnalysisResult {
  document_id: number;
  status: string;
  model: string;
  analysis: PaperAnalysis["data"];
}

export interface LibraryListParams {
  project_id?: number | null;
  kind?: "document" | "image";
  reading_status?: "unread" | "reading" | "read";
  meta_status?: "pending" | "running" | "done" | "failed";
  tag?: string[];
  q?: string;
  sort?: "recent" | "title" | "authors" | "year" | "reading_status" | "size";
  order?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

export interface LibraryListResponse {
  total: number;
  offset: number;
  limit: number;
  items: UserFile[];
}

export interface LibraryTag {
  tag: string;
  count: number;
}

export interface LibraryStats {
  total_papers: number;
  total_images: number;
  unread: number;
  reading: number;
  read: number;
  analysis_done: number;
  analysis_pending: number;
  top_tags: LibraryTag[];
}

function buildLibraryQuery(params: LibraryListParams): string {
  const p = new URLSearchParams();
  if (params.project_id != null) p.set("project_id", String(params.project_id));
  if (params.kind)           p.set("kind", params.kind);
  if (params.reading_status) p.set("reading_status", params.reading_status);
  if (params.meta_status)    p.set("meta_status", params.meta_status);
  if (params.q)              p.set("q", params.q);
  if (params.sort)           p.set("sort", params.sort);
  if (params.order)          p.set("order", params.order);
  if (params.limit != null)  p.set("limit", String(params.limit));
  if (params.offset != null) p.set("offset", String(params.offset));
  // multi-value tags
  for (const t of params.tag ?? []) p.append("tag", t);
  const qs = p.toString();
  return qs ? `/api/files?${qs}` : "/api/files";
}

export const filesApi = {
  // ── Library listing (M5) ──
  list: (params: LibraryListParams = {}) =>
    api.get<LibraryListResponse>(buildLibraryQuery(params)),

  // Simple flat list (used internally where pagination isn't needed)
  listAll: () =>
    api.get<LibraryListResponse>("/api/files?limit=500").then((r) => r.items),

  tags: (projectId?: number | null) => {
    const qs = projectId != null ? `?project_id=${projectId}` : "";
    return api.get<LibraryTag[]>(`/api/library/tags${qs}`);
  },

  stats: (projectId?: number | null) => {
    const qs = projectId != null ? `?project_id=${projectId}` : "";
    return api.get<LibraryStats>(`/api/library/stats${qs}`);
  },

  // ── Single file ──
  get: (id: number) => api.get<UserFile>(`/api/files/${id}`),
  patch: (
    id: number,
    body: Partial<Pick<UserFile,
      "title" | "authors" | "year" | "venue" | "doi" |
      "abstract" | "reading_status" | "tags"
    >>,
  ) => api.patch<UserFile>(`/api/files/${id}`, body),

  // ── Upload ──
  // Documents (pdf/epub/docx/txt) go through the JWT-authenticated, async
  // /api/documents/upload; everything else (images, for vision attachments)
  // stays on the original session-authenticated, synchronous /api/files —
  // the JWT route doesn't accept images at all.
  upload: async (
    file: File,
    conversationId?: number | null,
    projectId?: number | null
  ): Promise<UploadOutcome> => {
    const fd = new FormData();
    fd.append("file", file);
    if (conversationId != null) fd.append("conversation_id", String(conversationId));
    if (projectId != null)      fd.append("project_id", String(projectId));

    if (isDocumentUpload(file.name)) {
      const token = await getBearerToken();
      const result = await api.postForm<UploadDocumentResult>("/api/documents/upload", fd, token);
      return { async: true, result };
    }
    const result = await api.postForm<UploadResult>("/api/files", fd);
    return { async: false, result };
  },

  remove: (id: number) => api.delete<{ ok: boolean }>(`/api/files/${id}`),

  // ── Analysis ──
  getAnalysis: (id: number) =>
    api.get<PaperAnalysis>(`/api/files/${id}/analysis`),
  refreshAnalysis: (id: number) =>
    api.post<{ ok: boolean; status: string }>(`/api/files/${id}/analysis/refresh`),

  // JWT-authenticated, synchronous counterpart to refreshAnalysis above —
  // writes to the same PaperAnalysis row (keyed by file id) via a separate
  // prompt/model/cost-logging path, see backend/upload/routes.py.
  analyzeDocument: async (id: number): Promise<DocumentAnalysisResult> => {
    const token = await getBearerToken();
    return api.post<DocumentAnalysisResult>(`/api/documents/${id}/analysis`, undefined, token);
  },
};
