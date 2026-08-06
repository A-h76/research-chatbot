/**
 * Project workspace journey URLs + Writing Studio nav.
 *
 * Design principle: The Writing Studio should feel familiar enough that a
 * researcher can begin writing within two minutes, but intelligent enough
 * that after one week they cannot imagine doing research without Dhund.
 * Adopt the industry-standard three-pane research-writing interaction model;
 * differentiate via Research Intelligence — not unfamiliar chrome.
 */

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

export type JourneyNavId =
  | "library"
  | "papers"
  | "research"
  | "evidence"
  | "writing"
  | "chat"
  | "settings";

export type JourneyNavItem = {
  id: JourneyNavId;
  label: string;
  /** Build href for a project-scoped Writing Studio sidebar. */
  href: (projectId: number) => string;
};

/** Writing Studio left nav — industry-standard research writing IA. */
export const PROJECT_JOURNEY_NAV: JourneyNavItem[] = [
  { id: "library", label: "Library", href: () => "/library" },
  { id: "papers", label: "Papers", href: (id) => projectHubUrl(id, "papers") },
  { id: "research", label: "Research", href: (id) => projectHubUrl(id, "research") },
  { id: "evidence", label: "Evidence", href: (id) => projectEvidenceUrl(id) },
  { id: "writing", label: "Writing", href: (id) => projectWritingUrl(id) },
  { id: "chat", label: "Chat", href: (id) => projectHubUrl(id, "chat") },
];

export function isWritingStudioPath(path: string): boolean {
  return path === "/writing" || path.startsWith("/writing/") || /\/projects\/\d+\/writing/.test(path);
}

/** Which journey item is active for the current route. */
export function resolveJourneyActive(
  path: string,
  search: string,
  projectId: number,
): JourneyNavId | null {
  const params = new URLSearchParams(search);
  const tab = params.get("tab");
  const focus = params.get("focus");

  if (path.startsWith("/settings") || path.startsWith("/admin")) return "settings";
  if (path.startsWith("/library") || path.startsWith("/files")) return "library";

  if (path.startsWith("/writing") || /\/projects\/\d+\/writing/.test(path)) {
    if (focus === "evidence" || focus === "review") return "evidence";
    return "writing";
  }

  if (path.startsWith(`/projects/${projectId}`)) {
    if (tab === "papers") return "papers";
    if (tab === "research" || tab === "compare") return "research";
    if (tab === "chat") return "chat";
    if (tab === "notes" || tab === "questions" || tab === "insights") return "papers";
    return "papers";
  }

  if (path.startsWith("/papers/")) {
    if (path.includes("/chat")) return "chat";
    return "papers";
  }

  if (path.startsWith("/c/") || path.startsWith("/chat")) return "chat";
  return null;
}

/** Count [#id] citation markers in manuscript text. */
export function countCitationMarkers(text: string): number {
  const matches = text.match(/\[#\d+\]/g);
  return matches?.length ?? 0;
}

/** Word count for status footer (whitespace-split). */
export function countWords(text: string): number {
  const t = text.trim();
  if (!t) return 0;
  return t.split(/\s+/).length;
}
