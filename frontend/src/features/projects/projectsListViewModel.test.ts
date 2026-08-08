import { describe, expect, it } from "vitest";
import {
  buildProjectsListView,
  papersPhrase,
  statusLabelFrom,
} from "./projectsListViewModel";
import type { Project } from "@/types/api";

const p = (id: number, name: string): Project =>
  ({
    id,
    name,
    emoji: "📁",
    description: "",
    instructions: "",
  }) as Project;

function state(partial: {
  id: number;
  title: string;
  papers: number;
  evidence?: number;
  stage: string;
  nextId: string;
  nextLabel: string;
  hasManuscript?: boolean;
}) {
  return {
    user: { experience: "intermediate", goals: [], fields: [] },
    project: { id: partial.id, title: partial.title },
    corpus: {
      papers: partial.papers,
      evidence: partial.evidence ?? 0,
      themes: 0,
      gaps: 0,
      contradictions: 0,
      coverage: null,
    },
    workflow: {
      stage: partial.stage,
      label: partial.stage,
      completion: { done: 2, total: 7 },
      nextAction: {
        id: partial.nextId,
        label: partial.nextLabel,
        href: "/x",
      },
      blockers: [],
    },
    writing: { hasManuscript: partial.hasManuscript ?? false },
  };
}

describe("statusLabelFrom", () => {
  it("uses outcome readiness for late journey stages", () => {
    expect(
      statusLabelFrom(
        state({
          id: 1,
          title: "A",
          papers: 9,
          evidence: 20,
          stage: "writing",
          nextId: "start_writing",
          nextLabel: "Start writing",
        }),
        9,
      ),
    ).toBe("Ready for writing");
    expect(
      statusLabelFrom(
        state({
          id: 1,
          title: "A",
          papers: 9,
          evidence: 20,
          stage: "review",
          nextId: "compare_papers",
          nextLabel: "Compare",
        }),
        9,
      ),
    ).toBe("Review before submission");
    expect(
      statusLabelFrom(
        state({
          id: 1,
          title: "A",
          papers: 9,
          evidence: 20,
          stage: "publish",
          nextId: "compare_papers",
          nextLabel: "Compare",
        }),
        9,
      ),
    ).toBe("Ready for publication");
  });
});

describe("buildProjectsListView", () => {
  it("promotes current project to Continue with milestone + unlocks", () => {
    const projects = [p(1, "Osteoarthritis"), p(2, "AI in Healthcare")];
    const statesById = new Map([
      [
        1,
        state({
          id: 1,
          title: "Osteoarthritis",
          papers: 6,
          stage: "evidence_extraction",
          nextId: "extract_evidence",
          nextLabel: "Extract evidence",
        }),
      ],
      [
        2,
        state({
          id: 2,
          title: "AI in Healthcare",
          papers: 9,
          evidence: 20,
          stage: "writing",
          nextId: "start_writing",
          nextLabel: "Start writing",
        }),
      ],
    ]);

    const view = buildProjectsListView({
      projects,
      currentProjectId: 1,
      statesById,
      fileCounts: new Map(),
    });

    expect(view.continueRow?.project.id).toBe(1);
    expect(view.continueRow?.statusLabel).toBe("Evidence extraction");
    expect(view.continueRow?.nextLabel).toBe("Extract evidence");
    expect(view.continueRow?.unlocksHint).toContain("Research Intelligence");
    expect(view.continueRow?.unlocksHint?.toLowerCase()).toContain("after extraction");
    expect(view.continueRow?.papers).toBe(6);
    expect(view.otherRows).toHaveLength(1);
    expect(view.otherRows[0].statusLabel).toBe("Ready for writing");
  });

  it("falls back to first project when none is scoped", () => {
    const view = buildProjectsListView({
      projects: [p(9, "A"), p(8, "B")],
      currentProjectId: null,
      statesById: new Map(),
      fileCounts: new Map([
        [9, 2],
        [8, 4],
      ]),
    });
    expect(view.continueRow?.project.id).toBe(9);
    expect(view.continueRow?.papers).toBe(2);
    expect(view.continueRow?.statusLabel).toBe("In progress");
  });
});

describe("papersPhrase", () => {
  it("labels papers in words", () => {
    expect(papersPhrase(1)).toBe("1 paper");
    expect(papersPhrase(6)).toBe("6 papers");
  });
});
