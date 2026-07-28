import { api } from "@/lib/apiClient";

export interface LibraryCollection {
  id: number;
  name: string;
  description: string;
  parent_id: number | null;
  external_id: string;
  source: string;
  sort_order: number;
  paper_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export const collectionsApi = {
  list: () => api.get<{ items: LibraryCollection[] }>("/api/library/collections"),

  create: (body: { name: string; description?: string; parent_id?: number | null }) =>
    api.post<LibraryCollection>("/api/library/collections", body),

  update: (
    id: number,
    body: Partial<{ name: string; description: string; parent_id: number | null; sort_order: number }>,
  ) => api.patch<LibraryCollection>(`/api/library/collections/${id}`, body),

  remove: (id: number) => api.delete<{ ok: boolean }>(`/api/library/collections/${id}`),

  addPapers: (id: number, fileIds: number[]) =>
    api.post<{ ok: boolean; added: number; skipped: number; paper_count: number }>(
      `/api/library/collections/${id}/papers`,
      { file_ids: fileIds },
    ),
};

/** DELETE with JSON body — apiClient has no delete-with-body helper. */
export async function removePapersFromCollection(id: number, fileIds: number[]) {
  const res = await fetch(`/api/library/collections/${id}/papers`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_ids: fileIds }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || body.error || "request_failed");
  return body as { ok: boolean; removed: number; paper_count: number };
}
