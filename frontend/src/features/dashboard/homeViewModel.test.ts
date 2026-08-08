import { describe, expect, it } from "vitest";
import { buildHomeViewModel } from "./homeViewModel";

describe("buildHomeViewModel", () => {
  it("maps nextAction to Next step + outcome-focused detail", () => {
    const view = buildHomeViewModel({
      user: { experience: "intermediate", goals: [], fields: [] },
      project: { id: 1, title: "AI in Healthcare" },
      corpus: {
        papers: 9,
        evidence: 0,
        themes: 0,
        gaps: 0,
        contradictions: 0,
        coverage: null,
      },
      workflow: {
        stage: "evidence_extraction",
        label: "Evidence",
        completion: { done: 2, total: 7 },
        nextAction: {
          id: "extract_evidence",
          label: "Extract evidence",
          href: "/research/compare?tab=extract",
        },
        blockers: [],
      },
      writing: { hasManuscript: false },
    });
    expect(view.status).toBe("Next step");
    expect(view.recommendation).toBe("Extract evidence");
    expect(view.context).toBe("9 papers");
    expect(view.projectTitle).toBe("AI in Healthcare");
    expect(view.lede).toContain("extracting evidence");
    expect(view.lede).toContain("9 papers");
    expect(view.detail.toLowerCase()).toContain("themes");
    expect(view.detail.toLowerCase()).toContain("gaps");
    expect(view.href).toContain("extract");
  });

  it("falls back without dumping metrics", () => {
    const view = buildHomeViewModel(null, { unread: 0, hasProject: false });
    expect(view.recommendation).toBe("Import papers");
    expect(view.status).toBe("Next step");
    expect(view.detail.toLowerCase()).toContain("corpus");
  });
});
