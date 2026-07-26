import { ApiError } from "@/lib/apiClient";
import type { PipelineErrorCode } from "./types";

/**
 * Typed error for Phase 1 pipeline HTTP calls.
 * Prefer this over alert() / toast inside the data layer.
 */
export class PipelineError extends Error {
  readonly code: PipelineErrorCode;
  readonly status: number;
  readonly details?: string;

  constructor(code: PipelineErrorCode, status: number, details?: string) {
    super(details ? `${code}: ${details}` : code);
    this.name = "PipelineError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

function codeFromStatus(status: number, raw: string): PipelineErrorCode {
  if (status === 401) return "not_authenticated";
  if (status === 404) return "not_found";
  if (status === 400 && raw === "invalid_phase") return "invalid_phase";
  if (status === 502 || raw === "storage_unavailable") return "storage_unavailable";
  if (status >= 500) return "server_error";
  if (raw === "not_found") return "not_found";
  if (raw === "invalid_phase") return "invalid_phase";
  if (raw === "invalid_response") return "invalid_response";
  return "request_failed";
}

/** Map fetch / ApiError / unknown into PipelineError. */
export function toPipelineError(err: unknown): PipelineError {
  if (err instanceof PipelineError) return err;

  if (err instanceof ApiError) {
    return new PipelineError(codeFromStatus(err.status, err.message), err.status, err.message);
  }

  if (err instanceof TypeError) {
    // Typical offline / failed fetch
    return new PipelineError("network_error", 0, err.message);
  }

  if (err instanceof Error) {
    return new PipelineError("request_failed", 0, err.message);
  }

  return new PipelineError("request_failed", 0, String(err));
}

export function isPipelineError(err: unknown): err is PipelineError {
  return err instanceof PipelineError;
}
