/**
 * Home view model — Product Constitution: Invisible Intelligence.
 * Maps internal Research State → one status + one recommendation + one context.
 * Never expose full Research State on Home.
 *
 * Home answers: "What should I do next?"
 * Show outcomes, not bare actions.
 */

import type { AssistantTurnResponse } from "@/features/assistant/api";

export type HomeViewModel = {
  /** Section label above the recommendation (e.g. "Next step") */
  status: string;
  /** Primary recommendation title (CTA label) */
  recommendation: string;
  /** Why this matters — outcome-focused */
  detail: string;
  /** Single context chip (e.g. "9 papers") */
  context: string | null;
  /** Project title for greeting context, if any */
  projectTitle: string | null;
  /** Soft prose bridge under the greeting (e.g. "extracting evidence from your 9 papers") */
  lede: string | null;
  href: string;
};

type ResearchState = AssistantTurnResponse["research_state"];

function paperPhrase(n: number): string {
  return n === 1 ? "1 paper" : `${n} papers`;
}

/** Outcome copy — why the action matters, not just what to click. */
function outcomeDetail(
  actionId: string,
  papers: number,
  project: string | null | undefined,
): string {
  switch (actionId) {
    case "extract_evidence":
      return papers > 0
        ? `Unlock themes, research gaps, and evidence-backed writing from your ${paperPhrase(papers)}.`
        : "Unlock themes, research gaps, and evidence-backed writing from your imported papers.";
    case "import_papers":
      return "Bring papers into Dhund so the next steps are grounded in your corpus.";
    case "review_gaps":
      return "See where the literature is thin — and where your contribution can land.";
    case "inspect_contradictions":
      return "Resolve conflicting claims before they weaken your argument.";
    case "start_writing":
      return "Draft from accepted evidence while the corpus is still fresh.";
    case "unread_papers":
      return "Catch up so new findings feed the next evidence pass.";
    case "compare_papers":
      return "Side-by-side synthesis is the highest-leverage move with this corpus.";
    default:
      return project
        ? `Continue the research journey on ${project}.`
        : "Highest-impact next step for your research.";
  }
}

function ledeFor(
  actionId: string,
  label: string,
  papers: number,
): string {
  switch (actionId) {
    case "extract_evidence":
      return papers > 0
        ? `extracting evidence from your ${paperPhrase(papers)}`
        : "extracting evidence from your papers";
    case "import_papers":
      return "importing papers into your library";
    case "review_gaps":
      return "reviewing research gaps in your corpus";
    case "inspect_contradictions":
      return "inspecting contradictions across your papers";
    case "start_writing":
      return "starting a draft from your evidence";
    case "unread_papers":
      return papers > 0
        ? `catching up on unread papers`
        : "catching up on unread papers";
    case "compare_papers":
      return "comparing papers side by side";
    default: {
      const soft = label.trim().replace(/\.$/, "");
      return soft.charAt(0).toLowerCase() + soft.slice(1);
    }
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
    const project = state.project?.title ?? null;

    let context: string | null = null;
    if (project != null || papers > 0) {
      context = paperPhrase(papers);
    } else if ((fallback?.unread ?? 0) > 0) {
      context = `${fallback!.unread} unread`;
    }

    return {
      status: "Next step",
      recommendation: na.label,
      detail: outcomeDetail(na.id, papers, project),
      context,
      projectTitle: project,
      lede: ledeFor(na.id, na.label, papers),
      href: na.href || "/library",
    };
  }

  if ((fallback?.unread ?? 0) > 0) {
    return {
      status: "Next step",
      recommendation: "Catch up on unread papers",
      detail: "Catch up so new findings feed the next evidence pass.",
      context: `${fallback!.unread} unread`,
      projectTitle: null,
      lede: "catching up on unread papers",
      href: "/library?reading_status=unread",
    };
  }

  if (fallback?.hasProject) {
    return {
      status: "Next step",
      recommendation: "Continue your project",
      detail: "Pick up where you left off and keep momentum.",
      context: null,
      projectTitle: null,
      lede: "continuing your project",
      href: "/projects",
    };
  }

  return {
    status: "Next step",
    recommendation: "Import papers",
    detail: "Bring papers into Dhund so the next steps are grounded in your corpus.",
    context: null,
    projectTitle: null,
    lede: "importing papers into your library",
    href: "/library?upload=1#import",
  };
}
