import { describe, expect, it } from "vitest";
import type { UserFile } from "@/types/api";
import {
  isCrossPaperResearchReady,
  summarizeCrossPaperReadiness,
} from "./crossPaperResearchReady";

function file(overrides: Partial<UserFile> = {}): UserFile {
  return {
    id: 1,
    name: "paper.pdf",
    kind: "document",
    size: 100,
    project_id: 1,
    conversation_id: null,
    chunks: 5,
    title: "Paper",
    authors: "",
    year: "",
    venue: "",
    doi: "",
    abstract: "",
    reading_status: "unread",
    tags: [],
    meta_status: "done",
    created_at: null,
    ...overrides,
  };
}

describe("crossPaperResearchReady", () => {
  it("treats only paper_analysis_status done as ready", () => {
    expect(isCrossPaperResearchReady(file({ meta_status: "done" }))).toBe(false);
    expect(
      isCrossPaperResearchReady(
        file({ meta_status: "done", paper_analysis_status: "done" }),
      ),
    ).toBe(true);
    expect(
      isCrossPaperResearchReady(
        file({ cross_paper_research_ready: true, paper_analysis_status: "pending" }),
      ),
    ).toBe(true);
  });

  it("summarizes ready vs pending counts", () => {
    const summary = summarizeCrossPaperReadiness([
      file({ id: 1, paper_analysis_status: "done" }),
      file({ id: 2, paper_analysis_status: "running" }),
      file({ id: 3, paper_analysis_status: "done" }),
    ]);
    expect(summary.readyCount).toBe(2);
    expect(summary.pendingCount).toBe(1);
    expect(summary.total).toBe(3);
  });
});
