/**
 * Projects list view model — Constitution: Invisible Intelligence.
 * Answers: "Which research should I advance?"
 * Bookshelf metaphor: what · where you stopped · what continues.
 * Outcome-oriented status — never dump Research State.
 */

import type { AssistantTurnResponse } from "@/features/assistant/api";
import type { Project } from "@/types/api";

type ResearchState = AssistantTurnResponse["research_state"];

export type ProjectListRow = {
  project: Project;
  papers: number;
  /**
   * Outcome-oriented orientation (e.g. "Ready for writing").
   * Prefer this over raw stage ids.
   */
  statusLabel: string;
  /** Next milestone — featured Continue leads with this */
  nextLabel: string | null;
  /** Quiet unlocks hint for early corpus work (Continue only) */
  unlocksHint: string | null;
  href: string;
};

export type ProjectsListView = {
  continueRow: ProjectListRow | null;
  otherRows: ProjectListRow[];
};

function paperCount(
  projectId: number,
  state: ResearchState | null | undefined,
  fileCounts: Map<number, number>,
): number {
  if (state?.corpus?.papers != null) return state.corpus.papers;
  return fileCounts.get(projectId) ?? 0;
}

/** Adaptive, outcome-oriented — late journey reads as readiness, not a stage machine. */
export function statusLabelFrom(
  state: ResearchState | null | undefined,
  papers: number,
): string {
  const stage = state?.workflow?.stage;
  const actionId = state?.workflow?.nextAction?.id;

  if (stage === "publish") return "Ready for publication";
  if (stage === "review") return "Review before submission";
  if (stage === "writing" || actionId === "start_writing") return "Ready for writing";
  if (stage === "synthesis" || actionId === "review_gaps" || actionId === "compare_papers") {
    return "Ready to synthesize";
  }
  if (stage === "evidence_extraction" || actionId === "extract_evidence") {
    return "Evidence extraction";
  }
  if (stage === "library" || actionId === "import_papers" || papers <= 0) {
    return "Building your library";
  }
  if (stage === "discovery") return "Getting started";
  if (papers <= 0) return "Building your library";
  return "In progress";
}

function nextLabelFrom(state: ResearchState | null | undefined): string | null {
  const label = state?.workflow?.nextAction?.label?.trim();
  return label || null;
}

function unlocksHintFrom(state: ResearchState | null | undefined): string | null {
  const stage = state?.workflow?.stage;
  const actionId = state?.workflow?.nextAction?.id;
  if (stage === "evidence_extraction" || actionId === "extract_evidence") {
    return "Unlocks themes · Research Intelligence · writing";
  }
  if (stage === "library" || actionId === "import_papers") {
    return "Unlocks evidence extraction and Research Intelligence";
  }
  return null;
}

function hrefFrom(state: ResearchState | null | undefined, projectId: number): string {
  const href = state?.workflow?.nextAction?.href?.trim();
  if (href) return href;
  return `/projects/${projectId}`;
}

function toRow(
  project: Project,
  state: ResearchState | null | undefined,
  fileCounts: Map<number, number>,
): ProjectListRow {
  const papers = paperCount(project.id, state, fileCounts);
  return {
    project,
    papers,
    statusLabel: statusLabelFrom(state, papers),
    nextLabel: nextLabelFrom(state),
    unlocksHint: unlocksHintFrom(state),
    href: hrefFrom(state, project.id),
  };
}

/**
 * Prefer UI-scoped project as Continue; else first in list.
 * Research State map is optional — rows still render with paper counts.
 */
export function buildProjectsListView(opts: {
  projects: Project[];
  currentProjectId: number | null;
  statesById: Map<number, ResearchState | null | undefined>;
  fileCounts: Map<number, number>;
}): ProjectsListView {
  const { projects, currentProjectId, statesById, fileCounts } = opts;
  if (projects.length === 0) {
    return { continueRow: null, otherRows: [] };
  }

  const continueId =
    currentProjectId != null && projects.some((p) => p.id === currentProjectId)
      ? currentProjectId
      : projects[0].id;

  const continueProject = projects.find((p) => p.id === continueId)!;
  const continueRow = toRow(
    continueProject,
    statesById.get(continueId),
    fileCounts,
  );
  const otherRows = projects
    .filter((p) => p.id !== continueId)
    .map((p) => toRow(p, statesById.get(p.id), fileCounts));

  return { continueRow, otherRows };
}

export function papersPhrase(n: number): string {
  return n === 1 ? "1 paper" : `${n} papers`;
}
