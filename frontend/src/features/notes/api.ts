import { api } from "@/lib/apiClient";
import type { Note, NoteListResponse } from "@/types/api";

export interface NoteListParams {
  project_id?: number | null;
  file_id?: number | null;
  q?: string;
  limit?: number;
  offset?: number;
}

export interface NoteInput {
  title?: string;
  content: string;
  project_id?: number | null;
  file_id?: number | null;
}

function buildQuery(params: NoteListParams): string {
  const p = new URLSearchParams();
  if (params.project_id != null) p.set("project_id", String(params.project_id));
  if (params.file_id    != null) p.set("file_id",    String(params.file_id));
  if (params.q)                  p.set("q",          params.q);
  if (params.limit  != null)     p.set("limit",      String(params.limit));
  if (params.offset != null)     p.set("offset",     String(params.offset));
  const qs = p.toString();
  return qs ? `/api/notes?${qs}` : "/api/notes";
}

export const notesApi = {
  list:   (params: NoteListParams = {}) =>
            api.get<NoteListResponse>(buildQuery(params)),
  get:    (id: number)               => api.get<Note>(`/api/notes/${id}`),
  create: (body: NoteInput)          => api.post<Note>("/api/notes", body),
  update: (id: number, body: Partial<NoteInput>) =>
            api.patch<Note>(`/api/notes/${id}`, body),
  remove: (id: number)               => api.delete<{ ok: boolean }>(`/api/notes/${id}`),
};
