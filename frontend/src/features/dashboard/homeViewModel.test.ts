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
    expect(view.status).toBe("Next milestone");
    expect(view.recommendation).toBe("Extract Evidence");
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
    expect(view.recommendation).toBe("Import Papers");
    expect(view.status).toBe("Next milestone");
    expect(view.detail.toLowerCase()).toContain("corpus");
  });

  it("uses unread context for import papers", () => {
    const view = buildHomeViewModel(
      {
        user: { experience: "intermediate", goals: [], fields: [] },
        project: { id: 1, title: "Literature Review: Osteoarthritis" },
        corpus: {
          papers: 0,
          evidence: 0,
          themes: 0,
          gaps: 0,
          contradictions: 0,
          coverage: null,
        },
        workflow: {
          stage: "library",
          label: "Library",
          completion: { done: 1, total: 7 },
          nextAction: {
            id: "import_papers",
            label: "Import papers",
            href: "/library?upload=1#import",
          },
          blockers: [],
        },
        writing: { hasManuscript: false },
      },
      { unread: 21 },
    );
    expect(view.recommendation).toBe("Import Papers");
    expect(view.detail.toLowerCase()).toContain("research intelligence");
    expect(view.context).toBe("21 unread papers");
  });
});
