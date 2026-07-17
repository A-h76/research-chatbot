import { api } from "@/lib/apiClient";
import type { Citation, CitationFormat } from "@/types/api";

export interface CitationInput {
  title: string;
  authors: string;
  year: string;
  venue: string;
  doi: string;
  url: string;
  notes?: string;
  project_id?: number | null;
}

export const citationsApi = {
  list: (params: { project_id?: number | null; q?: string } = {}) => {
    const p = new URLSearchParams();
    if (params.project_id != null) p.set("project_id", String(params.project_id));
    if (params.q)                  p.set("q", params.q);
    const qs = p.toString();
    return api.get<Citation[]>(qs ? `/api/citations?${qs}` : "/api/citations");
  },
  get:    (id: number) => api.get<Citation>(`/api/citations/${id}`),
  create: (body: CitationInput) =>
            api.post<Citation>("/api/citations", body),
  update: (id: number, body: Partial<CitationInput>) =>
            api.patch<Citation>(`/api/citations/${id}`, body),
  remove: (id: number) =>
            api.delete<{ ok: boolean }>(`/api/citations/${id}`),
  fromPaper: (fileId: number, projectId?: number | null) =>
               api.post<Citation & { existing: boolean }>(
                 `/api/citations/from-paper/${fileId}`,
                 { project_id: projectId ?? null },
               ),
  exportUrl: (format: CitationFormat = "bibtex", projectId?: number | null) => {
    const p = new URLSearchParams({ format });
    if (projectId != null) p.set("project_id", String(projectId));
    return `/api/citations/export?${p}`;
  },
};
