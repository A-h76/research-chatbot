import { api } from "@/lib/apiClient";
import type { ExplainResponse, EvidenceObjectDTO } from "./types";

export const evidenceApi = {
  explain: (body: {
    document_id: number;
    project_id: number;
    block_id?: string;
    range_start?: number;
    range_end?: number;
    selected_text?: string;
  }) => api.post<ExplainResponse>("/api/evidence/explain", body),

  list: (projectId: number, opts?: { file_id?: number; status?: string }) => {
    const p = new URLSearchParams();
    if (opts?.file_id) p.set("file_id", String(opts.file_id));
    if (opts?.status) p.set("status", opts.status);
    const qs = p.toString();
    return api.get<{ items: EvidenceObjectDTO[]; count: number }>(
      `/api/projects/${projectId}/evidence${qs ? `?${qs}` : ""}`,
    );
  },

  createBinding: (
    documentId: number,
    body: {
      evidence_object_id: number;
      block_id?: string;
      range_start?: number;
      range_end?: number;
      selected_text?: string;
      relation?: string;
    },
  ) => api.post(`/api/documents/${documentId}/evidence-bindings`, body),

  review: (evidenceId: number, body: { status: string; reason?: string }) =>
    api.post(`/api/evidence/${evidenceId}/reviews`, body),

  extract: (projectId: number, fileId: number, force = false) =>
    api.post(`/api/projects/${projectId}/evidence/extract`, { file_id: fileId, force }),
};
