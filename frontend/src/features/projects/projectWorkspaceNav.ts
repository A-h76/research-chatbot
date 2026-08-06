/** Project workspace journey URLs — deep-link Writing desk without new routes. */

export type ProjectWorkspaceStage =
  | "papers"
  | "analysing"
  | "research"
  | "writing"
  | "ready";

export type ProjectWorkspaceStageInput = {
  papers: number;
  analysisReady: number;
  notes: number;
  openQuestions: number;
  insights: number;
  chats: number;
};

/** Heuristic research stage from hub stats (no backend enum). */
export function deriveProjectWorkspaceStage(
  input: ProjectWorkspaceStageInput,
): ProjectWorkspaceStage {
  if (input.papers <= 0) return "papers";
  if (input.analysisReady < 2) return "analysing";
  if (input.chats > 0 || input.notes > 0 || input.insights > 0) return "writing";
  if (input.openQuestions > 0 || input.analysisReady >= 2) return "research";
  return "ready";
}

export function projectWorkspaceStageLabel(stage: ProjectWorkspaceStage): string {
  switch (stage) {
    case "papers":
      return "Add papers";
    case "analysing":
      return "Analysing";
    case "research":
      return "Research";
    case "writing":
      return "Writing";
    case "ready":
      return "Ready";
  }
}

export function projectHubUrl(
  projectId: number,
  tab?: "overview" | "papers" | "research" | "notes" | "questions" | "insights" | "chat",
): string {
  if (!tab || tab === "overview") return `/projects/${projectId}`;
  return `/projects/${projectId}?tab=${tab}`;
}

/** /projects/:id/writing preserves query (redirect → /writing?…). */
export function projectWritingUrl(
  projectId: number,
  opts?: { focus?: "evidence" | "review"; tab?: "export" | "draft"; action?: "lit-review" },
): string {
  const params = new URLSearchParams();
  if (opts?.focus) params.set("focus", opts.focus);
  if (opts?.tab && opts.tab !== "draft") params.set("tab", opts.tab);
  if (opts?.action) params.set("action", opts.action);
  const qs = params.toString();
  return qs
    ? `/projects/${projectId}/writing?${qs}`
    : `/projects/${projectId}/writing`;
}

export function projectEvidenceUrl(projectId: number): string {
  return projectWritingUrl(projectId, { focus: "evidence" });
}

export function projectReviewUrl(projectId: number): string {
  return projectWritingUrl(projectId, { focus: "review" });
}

export function projectExportUrl(projectId: number): string {
  return projectWritingUrl(projectId, { tab: "export" });
}
