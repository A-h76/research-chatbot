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
        product_label?: string;
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
        mediator_explanations?: Array<{ code: string; title: string; why: string }>;
        product_summary?: string | null;
        links: Array<{
          a_id: number;
          b_id: number;
          a_stance: string;
          b_stance: string;
          mediators: string[];
          why?: Array<{
            code: string;
            title: string;
            why: string;
            supporting_signals?: string[];
            contradicting_signals?: string[];
          }>;
          unexplained?: boolean;
        }>;
        pair_count: number;
        supporting_ids: number[];
        contradicting_ids: number[];
        metrics?: {
          mediated_pair_count?: number;
          unexplained_pair_count?: number;
          mediation_coverage?: number | null;
        };
      };
      consensus?: {
        label?: string;
        product_label?: string;
        supporting?: number;
        contradicting?: number;
        neutral?: number;
        [key: string]: unknown;
      };
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

  writing: (query: Record<string, unknown>) =>
    api.post<{
      query: Record<string, unknown>;
      objects: EvidenceObjectDTO[];
      total: number;
      truncated: boolean;
      stage: string;
      writing_version?: string;
      writing?: {
        status: "ok" | "blocked";
        blocked_reason: string | null;
        mode: string;
        paragraph: string | null;
        citations: Array<{
          evidence_id: number;
          file_id?: number;
          page?: number | null;
          claim: string;
          quote: string;
        }>;
        warnings: string[];
        disclaimer: string;
        supporting_count?: number;
      };
      reasoning?: Record<string, unknown>;
      conflict?: Record<string, unknown>;
      consensus?: Record<string, unknown>;
    }>("/api/evidence/writing", query),

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

  /** RI-002 Evidence Matrix (JSON). */
  matrix: (projectId: number, opts?: { file_ids?: number[]; status?: string }) => {
    const p = new URLSearchParams();
    if (opts?.file_ids?.length) p.set("file_ids", opts.file_ids.join(","));
    if (opts?.status) p.set("status", opts.status);
    const qs = p.toString();
    return api.get<import("./types").EvidenceMatrixResponse>(
      `/api/projects/${projectId}/evidence/matrix${qs ? `?${qs}` : ""}`,
    );
  },

  /** RI-002 export download (markdown | csv). */
  matrixExportUrl: (
    projectId: number,
    format: "markdown" | "csv",
    opts?: { file_ids?: number[] },
  ) => {
    const p = new URLSearchParams({ format });
    if (opts?.file_ids?.length) p.set("file_ids", opts.file_ids.join(","));
    return `/api/projects/${projectId}/evidence/matrix?${p.toString()}`;
  },

  /** RI-001 Theme Discovery (JSON). */
  themes: (projectId: number, opts?: { file_ids?: number[]; status?: string }) => {
    const p = new URLSearchParams();
    if (opts?.file_ids?.length) p.set("file_ids", opts.file_ids.join(","));
    if (opts?.status) p.set("status", opts.status);
    const qs = p.toString();
    return api.get<import("./types").EvidenceThemesResponse>(
      `/api/projects/${projectId}/evidence/themes${qs ? `?${qs}` : ""}`,
    );
  },

  themesExportUrl: (projectId: number, format: "markdown" = "markdown") =>
    `/api/projects/${projectId}/evidence/themes?format=${format}`,

  /** RI-005 project knowledge graph. */
  graph: (projectId: number, opts?: { file_ids?: number[]; include_conflict?: boolean }) => {
    const p = new URLSearchParams();
    if (opts?.file_ids?.length) p.set("file_ids", opts.file_ids.join(","));
    if (opts?.include_conflict === false) p.set("include_conflict", "0");
    const qs = p.toString();
    return api.get<import("./types").EvidenceGraphResponse>(
      `/api/projects/${projectId}/evidence/graph${qs ? `?${qs}` : ""}`,
    );
  },

  /** RI-006 research gaps. */
  gaps: (projectId: number, opts?: { file_ids?: number[] }) => {
    const p = new URLSearchParams();
    if (opts?.file_ids?.length) p.set("file_ids", opts.file_ids.join(","));
    const qs = p.toString();
    return api.get<import("./types").EvidenceGapsResponse>(
      `/api/projects/${projectId}/evidence/gaps${qs ? `?${qs}` : ""}`,
    );
  },

  gapsExportUrl: (projectId: number, format: "markdown" = "markdown") =>
    `/api/projects/${projectId}/evidence/gaps?format=${format}`,

  /** RI-007 research timeline. */
  timeline: (projectId: number, opts?: { file_ids?: number[] }) => {
    const p = new URLSearchParams();
    if (opts?.file_ids?.length) p.set("file_ids", opts.file_ids.join(","));
    const qs = p.toString();
    return api.get<import("./types").EvidenceTimelineResponse>(
      `/api/projects/${projectId}/evidence/timeline${qs ? `?${qs}` : ""}`,
    );
  },

  timelineExportUrl: (projectId: number, format: "markdown" = "markdown") =>
    `/api/projects/${projectId}/evidence/timeline?format=${format}`,

  /** RI-008 methodology advisory. */
  methodology: (projectId: number, opts?: { file_ids?: number[] }) => {
    const p = new URLSearchParams();
    if (opts?.file_ids?.length) p.set("file_ids", opts.file_ids.join(","));
    const qs = p.toString();
    return api.get<import("./types").EvidenceMethodologyResponse>(
      `/api/projects/${projectId}/evidence/methodology${qs ? `?${qs}` : ""}`,
    );
  },

  methodologyExportUrl: (projectId: number, format: "markdown" = "markdown") =>
    `/api/projects/${projectId}/evidence/methodology?format=${format}`,
};
