import { describe, expect, it } from "vitest";
import {
  deriveProjectWorkspaceStage,
  projectEvidenceUrl,
  projectExportUrl,
  projectHubUrl,
  projectReviewUrl,
  projectWritingUrl,
  projectWorkspaceStageLabel,
} from "./projectWorkspaceNav";

describe("projectWorkspaceNav", () => {
  it("builds hub and writing deep-links", () => {
    expect(projectHubUrl(3)).toBe("/projects/3");
    expect(projectHubUrl(3, "papers")).toBe("/projects/3?tab=papers");
    expect(projectWritingUrl(3)).toBe("/projects/3/writing");
    expect(projectEvidenceUrl(3)).toBe("/projects/3/writing?focus=evidence");
    expect(projectReviewUrl(3)).toBe("/projects/3/writing?focus=review");
    expect(projectExportUrl(3)).toBe("/projects/3/writing?tab=export");
    expect(projectWritingUrl(3, { action: "lit-review" })).toBe(
      "/projects/3/writing?action=lit-review",
    );
  });

  it("derives workspace stage from hub-like stats", () => {
    expect(
      deriveProjectWorkspaceStage({
        papers: 0,
        analysisReady: 0,
        notes: 0,
        openQuestions: 0,
        insights: 0,
        chats: 0,
      }),
    ).toBe("papers");
    expect(
      deriveProjectWorkspaceStage({
        papers: 5,
        analysisReady: 1,
        notes: 0,
        openQuestions: 0,
        insights: 0,
        chats: 0,
      }),
    ).toBe("analysing");
    expect(
      deriveProjectWorkspaceStage({
        papers: 5,
        analysisReady: 3,
        notes: 0,
        openQuestions: 2,
        insights: 0,
        chats: 0,
      }),
    ).toBe("research");
    expect(
      deriveProjectWorkspaceStage({
        papers: 5,
        analysisReady: 3,
        notes: 1,
        openQuestions: 0,
        insights: 0,
        chats: 0,
      }),
    ).toBe("writing");
    expect(projectWorkspaceStageLabel("analysing")).toBe("Analysing");
  });
});
