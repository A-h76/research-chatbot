import { PIPELINE_PHASES } from "./types";
import type {
  PipelineDocument,
  PipelineDerived,
  PipelinePhaseName,
  PipelineUiState,
} from "./types";

export type AdaptPipelineOptions = {
  /**
   * When set and differs from `doc.content_hash`, mark as stale
   * (file changed since last Phase 1 run).
   */
  fileContentHash?: string | null;
  /**
   * True after POST /analyze returned 202 queued and we have not yet
   * observed a pipeline row (or still pending).
   */
  enqueuePending?: boolean;
};

function asPhaseName(name: string): PipelinePhaseName | null {
  return (PIPELINE_PHASES as readonly string[]).includes(name)
    ? (name as PipelinePhaseName)
    : null;
}

function emptyDerived(partial: Partial<PipelineDerived> & { uiState: PipelineUiState }): PipelineDerived {
  return {
    isAbsent: false,
    isQueued: false,
    isRunning: false,
    isReady: false,
    isStale: false,
    isError: false,
    currentPhase: null,
    completed: [],
    remaining: [...PIPELINE_PHASES],
    failedPhase: null,
    status: null,
    warnings: [],
    errors: [],
    ...partial,
  };
}

/**
 * Convert backend pipeline JSON (or absence) into derived flags for M3+ UI.
 * Semantic phase sets only — no percentages or presentation.
 */
export function adaptPipeline(
  doc: PipelineDocument | null,
  options: AdaptPipelineOptions = {},
): PipelineDerived {
  if (!doc) {
    if (options.enqueuePending) {
      return emptyDerived({
        uiState: "queued",
        isQueued: true,
      });
    }
    return emptyDerived({
      uiState: "absent",
      isAbsent: true,
    });
  }

  const present = new Set(
    doc.phases
      .map(asPhaseName)
      .filter((p): p is PipelinePhaseName => p !== null),
  );

  // Preserve canonical ladder order, not server key insertion order alone.
  const completed = PIPELINE_PHASES.filter((p) => present.has(p));
  const remaining = PIPELINE_PHASES.filter((p) => !present.has(p));
  const currentPhase = completed.length > 0 ? completed[completed.length - 1]! : null;
  const failedPhase = doc.status === "failed" ? currentPhase : null;

  const hashMismatch =
    Boolean(options.fileContentHash) &&
    Boolean(doc.content_hash) &&
    options.fileContentHash !== doc.content_hash;

  let uiState: PipelineUiState;
  if (doc.status === "failed") {
    uiState = "error";
  } else if (hashMismatch) {
    uiState = "stale";
  } else if (doc.status === "pending") {
    uiState = "queued";
  } else if (doc.status === "running") {
    uiState = "running";
  } else if (doc.status === "done" || doc.status === "partial") {
    uiState = "ready";
  } else {
    uiState = "running";
  }

  // Enqueue just fired and row still pending → keep queued signal
  if (options.enqueuePending && (doc.status === "pending" || completed.length === 0)) {
    uiState = "queued";
  }

  return emptyDerived({
    uiState,
    isAbsent: false,
    isQueued: uiState === "queued",
    isRunning: uiState === "running",
    isReady: uiState === "ready",
    isStale: uiState === "stale",
    isError: uiState === "error",
    currentPhase,
    completed,
    remaining,
    failedPhase,
    status: doc.status,
    warnings: doc.warnings ?? [],
    errors: doc.errors ?? [],
  });
}
