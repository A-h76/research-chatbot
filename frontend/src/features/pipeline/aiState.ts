/**
 * AI State Language — locked labels + mapping from M1 pipeline derived state.
 * DESIGN-SYSTEM.md §12 / UI-Architecture.md M3.
 */

import { adaptPipeline } from "./adapter";
import type { PipelineDerived, PipelineDocument, PipelinePhaseName } from "./types";

/** Locked UI copy — do not invent synonyms. */
export const AI_STATE_LABELS = {
  uploading: "Uploading",
  queued: "Queued",
  understanding: "Understanding",
  classifying: "Classifying",
  evidence_ready: "Evidence Ready",
  graph_ready: "Graph Ready",
  chat_ready: "Chat Ready",
  needs_attention: "Needs attention",
} as const;

export type AiStateId = keyof typeof AI_STATE_LABELS;

/** Stepper nodes (Needs attention is not a ladder step). */
export const AI_STEPPER_STAGES: Exclude<AiStateId, "needs_attention">[] = [
  "uploading",
  "queued",
  "understanding",
  "classifying",
  "evidence_ready",
  "graph_ready",
  "chat_ready",
];

export type AiStepperNodeState = "pending" | "active" | "complete" | "error";

export interface AiStateResolved {
  id: AiStateId;
  label: (typeof AI_STATE_LABELS)[AiStateId];
}

export interface ResolveAiStateInput {
  derived?: PipelineDerived | null;
  /** UserFile.meta_status when pipeline row is absent or as secondary signal. */
  metaStatus?: string | null;
  /** Client transfer in flight (Library upload queue). */
  uploading?: boolean;
  uploadFailed?: boolean;
}

function has(completed: PipelinePhaseName[], name: PipelinePhaseName) {
  return completed.includes(name);
}

function classifyBandDone(completed: PipelinePhaseName[]) {
  return has(completed, "classification") || has(completed, "analysis_context");
}

/** Furthest completed Ready / mid band for a non-running pipeline. */
export function readyHeadline(d: PipelineDerived): AiStateResolved {
  if (has(d.completed, "knowledge_graph") || d.status === "done") {
    return { id: "chat_ready", label: AI_STATE_LABELS.chat_ready };
  }
  if (has(d.completed, "evidence_grading")) {
    // Graph still pending → Evidence Ready (spec example).
    if (d.remaining.includes("knowledge_graph")) {
      return { id: "evidence_ready", label: AI_STATE_LABELS.evidence_ready };
    }
    return { id: "graph_ready", label: AI_STATE_LABELS.graph_ready };
  }
  if (classifyBandDone(d.completed)) {
    return { id: "classifying", label: AI_STATE_LABELS.classifying };
  }
  if (has(d.completed, "document_understanding")) {
    return { id: "understanding", label: AI_STATE_LABELS.understanding };
  }
  return { id: "queued", label: AI_STATE_LABELS.queued };
}

export function runningHeadline(d: PipelineDerived): AiStateResolved {
  const next = d.remaining[0];
  if (!next || next === "document_understanding") {
    return { id: "understanding", label: AI_STATE_LABELS.understanding };
  }
  if (next === "classification" || next === "analysis_context") {
    return { id: "classifying", label: AI_STATE_LABELS.classifying };
  }
  if (
    next === "medical_understanding" ||
    next === "evidence_grading" ||
    next === "prompt_assembly"
  ) {
    return classifyBandDone(d.completed)
      ? { id: "classifying", label: AI_STATE_LABELS.classifying }
      : { id: "understanding", label: AI_STATE_LABELS.understanding };
  }
  if (next === "knowledge_graph") {
    return { id: "evidence_ready", label: AI_STATE_LABELS.evidence_ready };
  }
  return readyHeadline(d);
}

/**
 * Researcher-facing progress line — what is happening *now*, not phase ids.
 * Returns null when idle/ready (no chrome needed).
 */
export function describePipelineProgress(
  derived?: PipelineDerived | null,
  metaStatus?: string | null,
): string | null {
  if (derived?.isError) return null;

  if (derived && !derived.isAbsent) {
    if (derived.isQueued) {
      return "In queue — analysis starts shortly. You can keep browsing this paper.";
    }
    if (derived.isRunning) {
      const next = derived.remaining[0];
      switch (next) {
        case undefined:
        case "document_understanding":
          return "Extracting structure, abstract, and method signals…";
        case "classification":
        case "analysis_context":
          return "Building research profile (domain, document type, study design)…";
        case "medical_understanding":
          return "Extracting entities and scientific signals…";
        case "evidence_grading":
          return "Assessing evidence quality where applicable…";
        case "knowledge_graph":
          return "Linking concepts into a knowledge graph…";
        case "prompt_assembly":
          return "Preparing chat context from extracted evidence…";
        default:
          return "Analysis in progress…";
      }
    }
    return null;
  }

  if (metaStatus === "pending") {
    return "Queued for analysis — tabs fill in as each stage completes.";
  }
  if (metaStatus === "running") {
    return "Analysis is running — this tab will update when its stage finishes.";
  }
  return null;
}

/**
 * Composite headline state for badges (Library / Dashboard / Project rows).
 */
export function resolveAiState(input: ResolveAiStateInput): AiStateResolved {
  if (input.uploading) {
    return { id: "uploading", label: AI_STATE_LABELS.uploading };
  }
  if (input.uploadFailed || input.metaStatus === "failed") {
    return { id: "needs_attention", label: AI_STATE_LABELS.needs_attention };
  }

  const d = input.derived;
  if (d?.isError) {
    return { id: "needs_attention", label: AI_STATE_LABELS.needs_attention };
  }

  if (d && !d.isAbsent) {
    if (d.isQueued) {
      return { id: "queued", label: AI_STATE_LABELS.queued };
    }
    if (d.isRunning) {
      return runningHeadline(d);
    }
    if (d.isReady || d.isStale) {
      return readyHeadline(d);
    }
  }

  if (input.metaStatus === "pending") {
    return { id: "queued", label: AI_STATE_LABELS.queued };
  }
  if (input.metaStatus === "running") {
    return { id: "understanding", label: AI_STATE_LABELS.understanding };
  }
  if (input.metaStatus === "done") {
    return { id: "chat_ready", label: AI_STATE_LABELS.chat_ready };
  }

  return { id: "queued", label: AI_STATE_LABELS.queued };
}

export function resolveAiStateFromDocument(
  doc: PipelineDocument | null,
  input: Omit<ResolveAiStateInput, "derived"> = {},
): AiStateResolved {
  return resolveAiState({
    ...input,
    derived: adaptPipeline(doc, {
      enqueuePending: input.metaStatus === "pending" && !doc,
    }),
  });
}

export interface AiStepperNode {
  id: Exclude<AiStateId, "needs_attention">;
  label: string;
  state: AiStepperNodeState;
}

function stageIndex(id: Exclude<AiStateId, "needs_attention">) {
  return AI_STEPPER_STAGES.indexOf(id);
}

function ladderActiveId(
  headline: AiStateResolved,
  derived: PipelineDerived | null | undefined,
): Exclude<AiStateId, "needs_attention"> {
  if (headline.id !== "needs_attention") return headline.id;
  if (!derived || derived.isAbsent) return "queued";
  if (derived.isQueued) return "queued";
  if (derived.isRunning) {
    const h = runningHeadline(derived);
    return h.id === "needs_attention" ? "understanding" : h.id;
  }
  const h = readyHeadline(derived);
  return h.id === "needs_attention" ? "queued" : h.id;
}

/**
 * Map pipeline derived → stepper node states (Paper Overview).
 *
 * Important: ``UserFile.meta_status === "done"`` only means upload/extract
 * finished (RAG chat can work). It must NOT paint Understanding→Chat Ready
 * as complete — those steps require Phase 1 ``document_understanding`` etc.
 */
export function resolveAiStepper(
  derived: PipelineDerived | null | undefined,
  opts: { uploading?: boolean; metaStatus?: string | null } = {},
): AiStepperNode[] {
  const hasPhase1 = Boolean(derived && !derived.isAbsent);

  // Don't let upload meta_status shortcut the Phase 1 ladder on the stepper.
  const stepperMeta = hasPhase1
    ? opts.metaStatus
    : opts.metaStatus === "done"
      ? null
      : opts.metaStatus;

  const headline = resolveAiState({
    derived: derived ?? null,
    uploading: opts.uploading,
    metaStatus: stepperMeta,
  });

  const error = headline.id === "needs_attention";
  const activeId = opts.uploading ? "uploading" : ladderActiveId(headline, derived);
  const activeIdx = stageIndex(activeId);

  const pipelineFullyDone =
    hasPhase1 &&
    !error &&
    (derived!.status === "done" ||
      (Boolean(derived!.isReady) &&
        derived!.remaining.length === 0 &&
        has(derived!.completed, "knowledge_graph")));

  // Upload finished, Phase 1 never run → next real step is Understanding.
  if (!hasPhase1 && !opts.uploading && opts.metaStatus === "done") {
    return AI_STEPPER_STAGES.map((id) => ({
      id,
      label: AI_STATE_LABELS[id],
      state:
        id === "uploading" || id === "queued"
          ? "complete"
          : id === "understanding"
            ? "active"
            : "pending",
    }));
  }

  const allComplete = pipelineFullyDone;

  return AI_STEPPER_STAGES.map((id, idx) => {
    let state: AiStepperNodeState = "pending";

    if (allComplete) {
      state = "complete";
    } else if (opts.uploading && id === "uploading") {
      state = "active";
    } else if (id === "uploading") {
      state = "complete";
    } else if (idx < activeIdx) {
      state = "complete";
    } else if (idx === activeIdx) {
      state = error ? "error" : "active";
    }

    return { id, label: AI_STATE_LABELS[id], state };
  });
}

/** Token class names for badge/stepper chrome (DESIGN-SYSTEM §2.3.1). */
export function aiStateTokenClass(id: AiStateId): {
  dot: string;
  text: string;
  pulse: boolean;
} {
  switch (id) {
    case "uploading":
      return { dot: "bg-sem-info", text: "text-sem-info", pulse: true };
    case "queued":
      return { dot: "border-2 border-sem-queued bg-transparent", text: "text-sem-queued", pulse: false };
    case "understanding":
    case "classifying":
      return { dot: "bg-sem-running", text: "text-sem-running", pulse: true };
    case "evidence_ready":
    case "graph_ready":
      return { dot: "bg-sem-ready", text: "text-sem-ready", pulse: false };
    case "chat_ready":
      return { dot: "bg-signal-600", text: "text-signal-600", pulse: false };
    case "needs_attention":
      return { dot: "bg-sem-error", text: "text-sem-error", pulse: false };
  }
}

/** Tiny helper for upload-queue rows that only know a coarse M2 status. */
export function aiStateFromUploadStatus(
  status: "uploading" | "uploaded" | "failed",
): AiStateResolved {
  if (status === "uploading") return resolveAiState({ uploading: true });
  if (status === "failed") return resolveAiState({ uploadFailed: true });
  return resolveAiState({ metaStatus: "pending" }); // Uploaded → Queued until pipeline advances
}
