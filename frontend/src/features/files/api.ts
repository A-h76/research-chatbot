import { api } from "@/lib/apiClient";
import type { PaperAnalysis, UserFile } from "@/types/api";

export interface UploadResult extends UserFile {
  note?: string | null;
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
  upload: (file: File, conversationId?: number | null, projectId?: number | null) => {
    const fd = new FormData();
    fd.append("file", file);
    if (conversationId != null) fd.append("conversation_id", String(conversationId));
    if (projectId != null)      fd.append("project_id", String(projectId));
    return api.postForm<UploadResult>("/api/files", fd);
  },

  remove: (id: number) => api.delete<{ ok: boolean }>(`/api/files/${id}`),

  // ── Analysis ──
  getAnalysis: (id: number) =>
    api.get<PaperAnalysis>(`/api/files/${id}/analysis`),
  refreshAnalysis: (id: number) =>
    api.post<{ ok: boolean; status: string }>(`/api/files/${id}/analysis/refresh`),
};
