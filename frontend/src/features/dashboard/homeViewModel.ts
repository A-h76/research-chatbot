/**
 * Home view model — Product Constitution: Invisible Intelligence.
 * Maps internal Research State → one status + one recommendation + one context.
 * Never expose full Research State on Home.
 */

import type { AssistantTurnResponse } from "@/features/assistant/api";

export type HomeViewModel = {
  /** Short status word/phrase */
  status: string;
  /** Primary recommendation title (CTA label) */
  recommendation: string;
  /** Supporting one-liner */
  detail: string;
  /** Single context chip (e.g. "9 papers") */
  context: string | null;
  href: string;
};

type ResearchState = AssistantTurnResponse["research_state"];

function statusFromStage(stage: string | undefined, papers: number): string {
  switch (stage) {
    case "discovery":
      return "Getting started";
    case "library":
      return papers > 0 ? "Library" : "Getting started";
    case "evidence_extraction":
      return "Needs evidence";
    case "synthesis":
      return "Ready to synthesize";
    case "writing":
      return "Writing";
    case "review":
      return "Needs review";
    case "publish":
      return "Ready";
    default:
      return papers > 0 ? "In progress" : "Getting started";
  }
}

/** Prefer Assistant Engine nextAction; fall back for empty/offline. */
export function buildHomeViewModel(
  state: ResearchState | null | undefined,
  fallback?: { unread?: number; hasProject?: boolean },
): HomeViewModel {
  if (state?.workflow?.nextAction) {
    const na = state.workflow.nextAction;
    const papers = state.corpus?.papers ?? 0;
    const project = state.project?.title;
    const detail =
      project != null
        ? `Continue on ${project}.`
        : papers === 0
          ? "Start by bringing papers into Dhund."
          : "Highest-impact next step for your research.";

    let context: string | null = null;
    if (project) {
      context = papers === 1 ? "1 paper" : `${papers} papers`;
    } else if ((fallback?.unread ?? 0) > 0) {
      context = `${fallback!.unread} unread`;
    }

    return {
      status: statusFromStage(state.workflow.stage, papers),
      recommendation: na.label,
      detail,
      context,
      href: na.href || "/library",
    };
  }

  if ((fallback?.unread ?? 0) > 0) {
    return {
      status: "Library",
      recommendation: "Catch up on unread papers",
      detail: "A few papers are waiting in your library.",
      context: `${fallback!.unread} unread`,
      href: "/library?reading_status=unread",
    };
  }

  if (fallback?.hasProject) {
    return {
      status: "In progress",
      recommendation: "Open your project",
      detail: "Pick up where you left off.",
      context: null,
      href: "/projects",
    };
  }

  return {
    status: "Getting started",
    recommendation: "Import papers",
    detail: "Bring a few papers in — Dhund will guide the next step.",
    context: null,
    href: "/library?upload=1#import",
  };
}
