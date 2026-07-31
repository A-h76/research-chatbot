/** Paper Workspace tab IDs — URL strategy: `/papers/:id?tab=<id>` (default = overview). */

export const PAPER_TABS = [
  "overview",
  "structure",
  "classification",
  "entities",
  "evidence",
  "graph",
  "narrative",
  "related",
  "chat",
] as const;

export type PaperTabId = (typeof PAPER_TABS)[number];

export const PAPER_TAB_LABELS: Record<PaperTabId, string> = {
  overview: "Overview",
  structure: "Structure",
  classification: "Research Profile",
  entities: "Entities",
  evidence: "Evidence",
  graph: "Knowledge Graph",
  narrative: "Narrative",
  related: "Related Papers",
  chat: "Chat",
};

/** Tabs with real content in M4 (others are placeholders until later milestones). */
export const PAPER_TABS_WITH_CONTENT: ReadonlySet<PaperTabId> = new Set([
  "overview",
  "structure",
  "classification",
  "entities",
  "evidence",
  "graph",
  "narrative",
  "related",
  "chat", // opens existing PaperChatPage — not redesigned
]);

export function parsePaperTab(raw: string | null | undefined): PaperTabId {
  if (raw && (PAPER_TABS as readonly string[]).includes(raw)) {
    return raw as PaperTabId;
  }
  return "overview";
}

export function paperTabPanelId(tab: PaperTabId) {
  return `paper-tab-panel-${tab}`;
}

export function paperTabTriggerId(tab: PaperTabId) {
  return `paper-tab-${tab}`;
}
