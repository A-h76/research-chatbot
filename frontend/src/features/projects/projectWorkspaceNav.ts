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
  /** Deep-link into Writing’s evidence inspector — not a standalone nav destination. */
  return projectWritingUrl(projectId, { focus: "evidence" });
}

export function projectReviewUrl(projectId: number): string {
  return projectWritingUrl(projectId, { focus: "review" });
}

export function projectExportUrl(projectId: number): string {
  return projectWritingUrl(projectId, { tab: "export" });
}

/** Research Intelligence workbench (corpus analysis). */
export function projectResearchIntelligenceUrl(
  _projectId: number,
  tab?: string,
): string {
  if (!tab || tab === "overview") return "/research/compare";
  return `/research/compare?tab=${tab}`;
}

export type JourneyNavId =
  | "library"
  | "papers"
  | "research"
  | "writing"
  | "review"
  | "chat"
  | "settings";

export type JourneyNavItem = {
  id: JourneyNavId;
  label: string;
  /** Full brand label for tooltip / aria when rail truncates. */
  title?: string;
  /** Build href for a project-scoped Writing Studio sidebar. */
  href: (projectId: number) => string;
};

/**
 * Project workspace journey — research workflow only (no global Library).
 * Library lives in global nav / breadcrumbs once you're inside a project.
 *
 * Evidence is intentionally not a destination: it is cross-cutting inside
 * Papers, Research Intelligence, Writing, and Review.
 * Order: Papers → Research Intelligence → Writing → Review.
 */
export const PROJECT_JOURNEY_WORKFLOW: JourneyNavItem[] = [
  { id: "papers", label: "Papers", href: (id) => projectHubUrl(id, "papers") },
  {
    id: "research",
    label: "Research Intelligence",
    title: "Research Intelligence",
    href: (id) => projectResearchIntelligenceUrl(id),
  },
  { id: "writing", label: "Writing", href: (id) => projectWritingUrl(id) },
  { id: "review", label: "Review", href: (id) => projectReviewUrl(id) },
];

/** Secondary destinations below the research workflow divider. */
export const PROJECT_JOURNEY_SECONDARY: JourneyNavItem[] = [
  { id: "chat", label: "Chat", href: (id) => projectHubUrl(id, "chat") },
];

/** @deprecated Prefer PROJECT_JOURNEY_WORKFLOW + PROJECT_JOURNEY_SECONDARY */
export const PROJECT_JOURNEY_NAV: JourneyNavItem[] = [
  ...PROJECT_JOURNEY_WORKFLOW,
  ...PROJECT_JOURNEY_SECONDARY,
];

export function isWritingStudioPath(path: string): boolean {
  return path === "/writing" || path.startsWith("/writing/") || /\/projects\/\d+\/writing/.test(path);
}

/**
 * Project shell (journey sidebar) — inside a project environment.
 * Global Library / Home / Projects list keep the app-wide sidebar.
 */
export function isProjectWorkspacePath(path: string, projectId: number): boolean {
  if (isWritingStudioPath(path)) return true;
  if (path === `/projects/${projectId}` || path.startsWith(`/projects/${projectId}/`)) {
    return true;
  }
  // Paper detail while a project is selected — stay in project context
  if (path.startsWith("/papers/")) return true;
  // Research Intelligence workbench
  if (path.startsWith("/research") || path.startsWith("/analysis")) return true;
  return false;
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

  if (path.startsWith("/research") || path.startsWith("/analysis")) return "research";

  if (path.startsWith("/writing") || /\/projects\/\d+\/writing/.test(path)) {
    if (focus === "review") return "review";
    // focus=evidence opens the Writing assistant — still a Writing job.
    return "writing";
  }

  if (path.startsWith(`/projects/${projectId}`)) {
    if (tab === "papers") return "papers";
    // Hub console research tab — secondary to RI workbench; still highlight Intelligence
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
