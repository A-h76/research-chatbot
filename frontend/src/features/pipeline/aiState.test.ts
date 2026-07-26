import { describe, it, expect } from "vitest";
import { adaptPipeline } from "./adapter";
import {
  resolveAiState,
  resolveAiStepper,
  runningHeadline,
  readyHeadline,
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
