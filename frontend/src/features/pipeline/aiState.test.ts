import { describe, it, expect } from "vitest";
import { adaptPipeline } from "./adapter";
import {
  resolveAiState,
  resolveAiStepper,
  runningHeadline,
  readyHeadline,
  describePipelineProgress,
  AI_STATE_LABELS,
} from "./aiState";
import type { PipelineDocument, PipelineDerived } from "./types";

function doc(partial: Partial<PipelineDocument> & Pick<PipelineDocument, "status" | "phases">): PipelineDocument {
  return {
    file_id: 1,
    content_hash: "h",
    pipeline_version: "1",
    total_processing_time_ms: 1,
    warnings: [],
    errors: [],
    phase_results: Object.fromEntries(partial.phases.map((p) => [p, {}])),
    ...partial,
  };
}

describe("resolveAiState", () => {
  it("uses locked Uploading label during client transfer", () => {
    expect(resolveAiState({ uploading: true }).label).toBe("Uploading");
  });

  it("maps failed meta to Needs attention", () => {
    expect(resolveAiState({ metaStatus: "failed" }).label).toBe("Needs attention");
  });

  it("maps pending meta without pipeline to Queued", () => {
    expect(resolveAiState({ metaStatus: "pending" }).label).toBe("Queued");
  });

  it("maps running classify to Classifying", () => {
    const derived = adaptPipeline(
      doc({
        status: "running",
        phases: ["document_understanding"],
      }),
    );
    expect(runningHeadline(derived).label).toBe("Classifying");
    expect(resolveAiState({ derived }).label).toBe("Classifying");
  });

  it("maps evidence done / graph pending to Evidence Ready", () => {
    const derived = adaptPipeline(
      doc({
        status: "partial",
        phases: [
          "document_understanding",
          "classification",
          "analysis_context",
          "medical_understanding",
          "evidence_grading",
          "prompt_assembly",
        ],
      }),
    );
    expect(readyHeadline(derived).label).toBe("Evidence Ready");
  });

  it("maps full done pipeline to Chat Ready", () => {
    const derived = adaptPipeline(
      doc({
        status: "done",
        phases: [
          "document_understanding",
          "classification",
          "analysis_context",
          "medical_understanding",
          "evidence_grading",
          "prompt_assembly",
          "knowledge_graph",
        ],
      }),
    );
    expect(resolveAiState({ derived }).label).toBe("Chat Ready");
  });

  it("never invents Processing / Analyzing labels", () => {
    const labels = Object.values(AI_STATE_LABELS);
    expect(labels).not.toContain("Processing");
    expect(labels).not.toContain("Analyzing");
    expect(labels).not.toContain("Done");
  });
});

describe("resolveAiStepper", () => {
  it("marks Uploading complete and Queued active when pending", () => {
    const derived = adaptPipeline(null, { enqueuePending: true });
    const nodes = resolveAiStepper(derived);
    expect(nodes.find((n) => n.id === "uploading")?.state).toBe("complete");
    expect(nodes.find((n) => n.id === "queued")?.state).toBe("active");
  });

  it("marks all steps complete for Chat Ready", () => {
    const derived = adaptPipeline(
      doc({
        status: "done",
        phases: [
          "document_understanding",
          "classification",
          "analysis_context",
          "medical_understanding",
          "evidence_grading",
          "prompt_assembly",
          "knowledge_graph",
        ],
      }),
    );
    const nodes = resolveAiStepper(derived);
    expect(nodes.every((n) => n.state === "complete")).toBe(true);
  });

  it("does not paint Phase 1 complete when only upload meta_status is done", () => {
    const derived = adaptPipeline(null);
    const nodes = resolveAiStepper(derived, { metaStatus: "done" });
    expect(nodes.find((n) => n.id === "uploading")?.state).toBe("complete");
    expect(nodes.find((n) => n.id === "queued")?.state).toBe("complete");
    expect(nodes.find((n) => n.id === "understanding")?.state).toBe("active");
    expect(nodes.find((n) => n.id === "chat_ready")?.state).toBe("pending");
    expect(nodes.every((n) => n.state === "complete")).toBe(false);
  });

  it("marks error on the active ladder step", () => {
    const derived: PipelineDerived = {
      ...adaptPipeline(
        doc({ status: "failed", phases: ["document_understanding"] }),
      ),
      isError: true,
      uiState: "error",
    };
    const nodes = resolveAiStepper(derived);
    expect(nodes.some((n) => n.state === "error")).toBe(true);
  });
});

describe("describePipelineProgress", () => {
  it("explains queue and running stages without phase ids", () => {
    const queued = adaptPipeline(doc({ status: "pending", phases: [] }));
    expect(describePipelineProgress(queued)).toMatch(/queue/i);
    expect(describePipelineProgress(queued)).not.toMatch(/document_understanding/);

    const running = adaptPipeline(
      doc({ status: "running", phases: ["document_understanding"] }),
    );
    // remaining should start at classification after DU completes in phases list —
    // adaptPipeline derives remaining from status; assert human copy only.
    const hint = describePipelineProgress(running);
    expect(hint).toBeTruthy();
    expect(hint).not.toMatch(/_/);
  });

  it("returns null when ready", () => {
    const ready = adaptPipeline(
      doc({
        status: "done",
        phases: [
          "document_understanding",
          "classification",
          "analysis_context",
          "evidence_grading",
          "knowledge_graph",
        ],
      }),
    );
    expect(describePipelineProgress(ready)).toBeNull();
  });
});
