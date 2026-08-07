import { describe, expect, it } from "vitest";
import {
  countCitationMarkers,
  countWords,
  deriveProjectWorkspaceStage,
  isWritingStudioPath,
  projectEvidenceUrl,
  projectExportUrl,
  projectHubUrl,
  projectReviewUrl,
  projectWritingUrl,
  projectWorkspaceStageLabel,
  resolveJourneyActive,
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

  it("detects writing studio paths and journey active states", () => {
    expect(isWritingStudioPath("/writing")).toBe(true);
    expect(isWritingStudioPath("/projects/3/writing")).toBe(true);
    expect(isWritingStudioPath("/projects/3")).toBe(false);

    expect(resolveJourneyActive("/writing", "", 3)).toBe("writing");
    expect(resolveJourneyActive("/writing", "?focus=evidence", 3)).toBe("evidence");
    expect(resolveJourneyActive("/writing", "?focus=review", 3)).toBe("review");
    expect(resolveJourneyActive("/library", "", 3)).toBe("library");
    expect(resolveJourneyActive("/projects/3", "?tab=research", 3)).toBe("research");
    expect(resolveJourneyActive("/research/compare", "", 3)).toBe("research");
    expect(resolveJourneyActive("/research/compare", "?tab=matrix", 3)).toBe("research");
    expect(resolveJourneyActive("/analysis/compare", "", 3)).toBe("research");
    expect(resolveJourneyActive("/projects/3", "?tab=chat", 3)).toBe("chat");
    expect(resolveJourneyActive("/settings", "", 3)).toBe("settings");
  });

  it("detects project workspace shell paths", async () => {
    const {
      isProjectWorkspacePath,
      PROJECT_JOURNEY_WORKFLOW,
      PROJECT_JOURNEY_NAV,
      projectResearchIntelligenceUrl,
    } = await import("./projectWorkspaceNav");
    expect(isProjectWorkspacePath("/projects/3/writing", 3)).toBe(true);
    expect(isProjectWorkspacePath("/projects/3", 3)).toBe(true);
    expect(isProjectWorkspacePath("/papers/9", 3)).toBe(true);
    expect(isProjectWorkspacePath("/research/compare", 3)).toBe(true);
    expect(isProjectWorkspacePath("/analysis/compare", 3)).toBe(true);
    expect(isProjectWorkspacePath("/library", 3)).toBe(false);
    expect(isProjectWorkspacePath("/projects", 3)).toBe(false);
    expect(isProjectWorkspacePath("/projects/9", 3)).toBe(false);
    expect(PROJECT_JOURNEY_WORKFLOW.map((i) => i.id)).toEqual([
      "papers",
      "evidence",
      "research",
      "writing",
      "review",
    ]);
    expect(PROJECT_JOURNEY_WORKFLOW.find((i) => i.id === "research")?.label).toBe(
      "Research Intelligence",
    );
    expect(projectResearchIntelligenceUrl(3)).toBe("/research/compare");
    expect(projectResearchIntelligenceUrl(3, "matrix")).toBe("/research/compare?tab=matrix");
    expect(PROJECT_JOURNEY_NAV.some((i) => i.id === "library")).toBe(false);
  });

  it("counts words and citation markers", () => {
    expect(countWords("")).toBe(0);
    expect(countWords("hello world")).toBe(2);
    expect(countCitationMarkers("See [#12] and [#13].")).toBe(2);
    expect(countCitationMarkers("no cites")).toBe(0);
  });
});
