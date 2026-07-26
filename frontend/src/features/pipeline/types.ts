/**
 * Phase 1 analysis pipeline types — mirror backend/analysis_pipeline contracts.
 * Do not invent fields; see routes.py + models.AnalysisResult.to_api_dict().
 */

/** Canonical phase keys from backend `_VALID_PHASES`. */
export const PIPELINE_PHASES = [
  "document_understanding",
  "classification",
  "analysis_context",
  "medical_understanding",
  "evidence_grading",
  "prompt_assembly",
  "knowledge_graph",
] as const;

export type PipelinePhaseName = (typeof PIPELINE_PHASES)[number];

/** Persisted job status — `AnalysisJobStatus` in backend/analysis_pipeline/models.py */
export type PipelineStatus = "pending" | "running" | "done" | "failed" | "partial";

/** Opaque per-phase payload (shape varies by phase package). */
export type PhaseResult = Record<string, unknown>;

/** One named phase entry as returned inside `phase_results`. */
export interface PipelinePhase {
  name: PipelinePhaseName;
  result: PhaseResult;
}

/**
 * GET /api/documents/:id/pipeline body (= AnalysisResult.to_api_dict).
 * Optional `prompt_context` only when `?include_prompt_context=1`.
 */
export interface PipelineDocument {
  file_id: number;
  content_hash: string;
  status: PipelineStatus;
  pipeline_version: string;
  total_processing_time_ms: number;
  warnings: string[];
  errors: string[];
  /** Phase keys present in `phase_results` (server order). */
  phases: string[];
  phase_results: Record<string, PhaseResult>;
  prompt_context?: string;
}

/** GET /api/documents/:id/phases/:phase */
export interface PhaseResponse {
  document_id: number;
  phase: PipelinePhaseName;
  result: PhaseResult;
}

/** POST /api/documents/:id/analyze → 202 (default async enqueue). */
export interface AnalyzeQueuedResponse {
  status: "queued";
  job_id: number;
  document_id: number;
  job_type: string;
}

/**
 * POST …/analyze?sync=1 success body is a PipelineDocument.
 * (Backend may intend status "cached" on hash hit; unpack order currently
 * yields the stored job status — treat as PipelineDocument either way.)
 */
export type AnalyzeResponse = AnalyzeQueuedResponse | PipelineDocument;

export interface StartAnalysisBody {
  /** When true, run inline (?sync=1). Default false → 202 queued. */
  sync?: boolean;
  /** Ignore content_hash cache on sync path. */
  force?: boolean;
}

export interface GetPipelineOptions {
  includePromptContext?: boolean;
}

/** Architecture §7.6 UI machine states (derived; not a backend enum). */
export type PipelineUiState =
  | "absent"
  | "queued"
  | "running"
  | "ready"
  | "stale"
  | "error";

/** Frontend-friendly derived view of a pipeline document (no presentation). */
export interface PipelineDerived {
  uiState: PipelineUiState;
  isAbsent: boolean;
  isQueued: boolean;
  isRunning: boolean;
  isReady: boolean;
  isStale: boolean;
  isError: boolean;
  /**
   * Semantic “where we are” — last phase present in the server `phases` list,
   * or null when nothing has completed yet. Not a percentage.
   */
  currentPhase: PipelinePhaseName | null;
  /** Phases present in the pipeline row (canonical order filtered to known keys). */
  completed: PipelinePhaseName[];
  /** Known phases not yet in `completed` (canonical order). */
  remaining: PipelinePhaseName[];
  /** Set when status is failed and at least one phase exists. */
  failedPhase: PipelinePhaseName | null;
  status: PipelineStatus | null;
  warnings: string[];
  errors: string[];
}

export type PipelineErrorCode =
  | "not_found"
  | "not_authenticated"
  | "invalid_phase"
  | "invalid_response"
  | "network_error"
  | "server_error"
  | "storage_unavailable"
  | "request_failed";
