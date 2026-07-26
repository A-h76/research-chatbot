import { api, getBearerToken, ApiError } from "@/lib/apiClient";
import { PipelineError, toPipelineError } from "./errors";
import type {
  AnalyzeResponse,
  AnalyzeQueuedResponse,
  GetPipelineOptions,
  PhaseResponse,
  PipelineDocument,
  PipelinePhaseName,
  PipelineStatus,
  StartAnalysisBody,
} from "./types";
import { PIPELINE_PHASES } from "./types";

const STATUS_SET = new Set<PipelineStatus>([
  "pending",
  "running",
  "done",
  "failed",
  "partial",
]);

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function isPipelineDocument(v: unknown): v is PipelineDocument {
  if (!isRecord(v)) return false;
  if (typeof v.file_id !== "number") return false;
  if (typeof v.status !== "string" || !STATUS_SET.has(v.status as PipelineStatus)) return false;
  if (!isRecord(v.phase_results)) return false;
  if (!Array.isArray(v.phases)) return false;
  return true;
}

function isQueuedResponse(v: unknown): v is AnalyzeQueuedResponse {
  return (
    isRecord(v) &&
    v.status === "queued" &&
    typeof v.job_id === "number" &&
    typeof v.document_id === "number"
  );
}

function assertPipelineDocument(v: unknown, context: string): PipelineDocument {
  if (!isPipelineDocument(v)) {
    throw new PipelineError("invalid_response", 0, `Invalid pipeline payload (${context})`);
  }
  return {
    file_id: v.file_id,
    content_hash: typeof v.content_hash === "string" ? v.content_hash : "",
    status: v.status,
    pipeline_version: typeof v.pipeline_version === "string" ? v.pipeline_version : "",
    total_processing_time_ms:
      typeof v.total_processing_time_ms === "number" ? v.total_processing_time_ms : 0,
    warnings: Array.isArray(v.warnings) ? v.warnings.map(String) : [],
    errors: Array.isArray(v.errors) ? v.errors.map(String) : [],
    phases: v.phases.map(String),
    phase_results: v.phase_results as PipelineDocument["phase_results"],
    ...(typeof v.prompt_context === "string" ? { prompt_context: v.prompt_context } : {}),
  };
}

function assertPhaseResponse(v: unknown, phase: PipelinePhaseName): PhaseResponse {
  if (!isRecord(v) || typeof v.document_id !== "number" || !("result" in v)) {
    throw new PipelineError("invalid_response", 0, `Invalid phase payload (${phase})`);
  }
  const result = isRecord(v.result) ? (v.result as PhaseResponse["result"]) : {};
  return {
    document_id: v.document_id,
    phase: (typeof v.phase === "string" ? v.phase : phase) as PipelinePhaseName,
    result,
  };
}

async function withJwt<T>(fn: (token: string) => Promise<T>): Promise<T> {
  try {
    const token = await getBearerToken();
    return await fn(token);
  } catch (err) {
    throw toPipelineError(err);
  }
}

export function isPipelinePhaseName(value: string): value is PipelinePhaseName {
  return (PIPELINE_PHASES as readonly string[]).includes(value);
}

/**
 * Typed client for Phase 1 pipeline HTTP routes.
 * All routes are `@jwt_required()` — Bearer from `/api/auth/jwt`.
 */
export const pipelineApi = {
  /**
   * GET /api/documents/:id/pipeline
   * Returns `null` when no Phase 1 row exists (404 not_found).
   */
  async getPipeline(
    documentId: number,
    options: GetPipelineOptions = {},
  ): Promise<PipelineDocument | null> {
    const qs = options.includePromptContext ? "?include_prompt_context=1" : "";
    try {
      const body = await withJwt((token) =>
        api.get<unknown>(`/api/documents/${documentId}/pipeline${qs}`, token),
      );
      return assertPipelineDocument(body, "getPipeline");
    } catch (err) {
      const pe = toPipelineError(err);
      if (pe.code === "not_found" || (err instanceof ApiError && err.status === 404)) {
        return null;
      }
      throw pe;
    }
  },

  /** GET /api/documents/:id/phases/:phase */
  async getPhase(documentId: number, phase: PipelinePhaseName): Promise<PhaseResponse> {
    if (!isPipelinePhaseName(phase)) {
      throw new PipelineError("invalid_phase", 400, phase);
    }
    try {
      const body = await withJwt((token) =>
        api.get<unknown>(`/api/documents/${documentId}/phases/${phase}`, token),
      );
      return assertPhaseResponse(body, phase);
    } catch (err) {
      throw toPipelineError(err);
    }
  },

  /**
   * POST /api/documents/:id/analyze
   * Default async → 202 queued. Pass `{ sync: true }` for inline run.
   */
  async startAnalysis(
    documentId: number,
    body: StartAnalysisBody = {},
  ): Promise<AnalyzeResponse> {
    const sync = Boolean(body.sync);
    const qs = sync ? "?sync=1" : "";
    const payload: Record<string, unknown> = {};
    if (body.force) payload.force = true;
    if (sync) payload.sync = true;

    try {
      const raw = await withJwt((token) =>
        api.post<unknown>(
          `/api/documents/${documentId}/analyze${qs}`,
          Object.keys(payload).length ? payload : {},
          token,
        ),
      );

      if (isQueuedResponse(raw)) {
        return {
          status: "queued",
          job_id: raw.job_id,
          document_id: raw.document_id,
          job_type: typeof raw.job_type === "string" ? raw.job_type : "phase1_analysis",
        };
      }

      return assertPipelineDocument(raw, "startAnalysis");
    } catch (err) {
      throw toPipelineError(err);
    }
  },
};
