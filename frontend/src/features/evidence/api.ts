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

  search: (query: Record<string, unknown>) =>
    api.post<{
      query: Record<string, unknown>;
      objects: EvidenceObjectDTO[];
      total: number;
      truncated: boolean;
      stage: string;
    }>("/api/evidence/search", query),

  retrieve: (query: Record<string, unknown>) =>
    api.post<{
      query: Record<string, unknown>;
      objects: EvidenceObjectDTO[];
      total: number;
      truncated: boolean;
      stage: string;
    }>("/api/evidence/retrieve", query),

  rank: (query: Record<string, unknown>) =>
    api.post<{
      query: Record<string, unknown>;
      objects: EvidenceObjectDTO[];
      total: number;
      truncated: boolean;
      stage: string;
      ranking_version?: string;
      ranking_strategy?: string;
    }>("/api/evidence/rank", query),

  consensus: (query: Record<string, unknown>) =>
    api.post<{
      query: Record<string, unknown>;
      objects: EvidenceObjectDTO[];
      total: number;
      truncated: boolean;
      stage: string;
      consensus_version?: string;
      consensus?: {
        label: string;
        supporting: number;
        contradicting: number;
        neutral: number;
        supporting_ids: number[];
        contradicting_ids: number[];
        neutral_ids: number[];
      };
      ranking_version?: string;
      ranking_strategy?: string;
    }>("/api/evidence/consensus", query),

  conflict: (query: Record<string, unknown>) =>
    api.post<{
      query: Record<string, unknown>;
      objects: EvidenceObjectDTO[];
      total: number;
      truncated: boolean;
      stage: string;
      conflict_version?: string;
      conflict?: {
        has_conflict: boolean;
        mediators: string[];
        links: Array<{
          a_id: number;
          b_id: number;
          a_stance: string;
          b_stance: string;
          mediators: string[];
        }>;
        pair_count: number;
        supporting_ids: number[];
        contradicting_ids: number[];
      };
      consensus?: Record<string, unknown>;
      ranking_version?: string;
      ranking_strategy?: string;
    }>("/api/evidence/conflict", query),

  reason: (query: Record<string, unknown>) =>
    api.post<{
      query: Record<string, unknown>;
      objects: EvidenceObjectDTO[];
      total: number;
      truncated: boolean;
      stage: string;
      reasoning_version?: string;
      reasoning?: {
        summary_code: string;
        sufficiency: string;
        steps: Array<{ step: string; detail: string; code?: string }>;
        evidence_ids: number[];
        mediator_labels: string[];
      };
      conflict?: Record<string, unknown>;
      consensus?: Record<string, unknown>;
      ranking_version?: string;
      ranking_strategy?: string;
    }>("/api/evidence/reason", query),

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
