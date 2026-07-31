/**
 * Explainable Chat mapper — thin orchestration over chat messages + workspace refs.
 *
 * Live Paper Chat contract (server.py /api/chat SSE) — W1 Trust Chat:
 *   message.content = answer markdown
 *   message.sources = web { title, url, snippet }[]
 *   message.references = WorkspaceReference[] (passage cites from research_retrieve)
 *   message.scope = ResearchScope dict (session_id reserved for W7)
 *
 * mapExplainableChat() only normalizes fields the backend actually returns.
 * WorkspaceReferences for the evidence rail are also built from M5–M9
 * ViewModels via buildWorkspaceRail().
 */

import type { PaperTabId } from "../tabs";
import type { DocumentUnderstandingView } from "./structure";
import type { ClassificationViewModel } from "./classification";
import type { EntitiesViewModel } from "./entities";
import type { EvidenceViewModel } from "./evidence";
import type { KnowledgeGraphViewModel } from "./graph";
import { asNumber, asString, asStringArray, isRecord } from "./shared";

export type WorkspaceTab = Extract<
  PaperTabId,
  "structure" | "classification" | "entities" | "evidence" | "graph"
>;

export type WorkspaceReferenceKind =
  | "passage"
  | "structure.section"
  | "classification.decision"
  | "entity"
  | "evidence.framework"
  | "evidence.outcome"
  | "graph.node"
  | "graph.edge";

/** Semantic link into the Paper Workspace — not a raw hyperlink. */
export type WorkspaceReference = {
  id: string;
  kind: WorkspaceReferenceKind;
  /** Stable identity within the destination ViewModel (not a transient UUID alone). */
  refId: string;
  label?: string;
  tab: WorkspaceTab;
  href?: string;
  metadata?: Record<string, unknown>;
};

export type ExplainableChatViewModel = {
  id: string;
  role: "user" | "assistant" | "system" | string;
  answer: string;
  reasoning?: string;
  confidence?: number;
  warnings: string[];
  references: WorkspaceReference[];
  metadata: Record<string, unknown>;
};

const KIND_SET = new Set<string>([
  "passage",
  "structure.section",
  "classification.decision",
  "entity",
  "evidence.framework",
  "evidence.outcome",
  "graph.node",
  "graph.edge",
]);

const TAB_BY_KIND: Record<WorkspaceReferenceKind, WorkspaceTab> = {
  passage: "structure",
  "structure.section": "structure",
  "classification.decision": "classification",
  entity: "entities",
  "evidence.framework": "evidence",
  "evidence.outcome": "evidence",
  "graph.node": "graph",
  "graph.edge": "graph",
};

export function workspaceHref(
  fileId: number,
  tab: WorkspaceTab,
  refId?: string,
): string {
  const params = new URLSearchParams({ tab });
  if (refId) params.set("ref", refId);
  return `/papers/${fileId}?${params.toString()}`;
}

/** Stable section identity shared by the rail and Structure tab focus. */
export function structureSectionRefId(section: {
  heading: string;
  sectionType?: string;
}): string {
  return section.sectionType
    ? `section:${section.sectionType}:${section.heading}`
    : `section:${section.heading}`;
}

/** Prefer sourceEntityId over transient graph node UUID. */
export function graphNodeRefId(node: {
  sourceEntityId?: string;
  type: string;
  key: string;
}): string {
  return node.sourceEntityId
    ? `source:${node.type}:${node.sourceEntityId}`
    : node.key;
}

/** Resolve a chat/graph refId to the current KnowledgeGraphViewModel node id. */
export function resolveGraphNodeId(
  view: KnowledgeGraphViewModel,
  refId: string,
): string | null {
  if (refId.startsWith("source:")) {
    const rest = refId.slice("source:".length);
    const colon = rest.indexOf(":");
    if (colon > 0) {
      const type = rest.slice(0, colon);
      const sourceEntityId = rest.slice(colon + 1);
      const match = view.nodes.find(
        (n) => n.type === type && n.sourceEntityId === sourceEntityId,
      );
      if (match) return match.id;
    }
  }
  const byKey = view.nodes.find((n) => n.key === refId);
  if (byKey) return byKey.id;
  const byId = view.nodes.find((n) => n.id === refId);
  return byId?.id ?? null;
}

function mapWorkspaceReference(
  raw: unknown,
  index: number,
  fileId?: number,
): WorkspaceReference | null {
  if (!isRecord(raw)) return null;
  const kindRaw = asString(raw.kind);
  if (!kindRaw || !KIND_SET.has(kindRaw)) return null;
  const kind = kindRaw as WorkspaceReferenceKind;
  const refId = asString(raw.refId) ?? asString(raw.ref_id);
  if (!refId) return null;
  const tab =
    (asString(raw.tab) as WorkspaceTab | undefined) &&
    ["structure", "classification", "entities", "evidence", "graph"].includes(String(raw.tab))
      ? (raw.tab as WorkspaceTab)
      : TAB_BY_KIND[kind];
  const label = asString(raw.label);
  const id = asString(raw.id) ?? `${kind}:${refId}:${index}`;
  const href =
    asString(raw.href) ?? (fileId != null ? workspaceHref(fileId, tab, refId) : undefined);
  const metadata = isRecord(raw.metadata) ? { ...raw.metadata } : undefined;
  return { id, kind, refId, label, tab, href, metadata };
}

export type ChatMessageLike = {
  id?: number | string;
  role?: string;
  content?: string;
  answer?: string;
  sources?: Array<{ title?: string; url?: string; snippet?: string }>;
  reasoning?: string | null;
  confidence?: number | null;
  warnings?: unknown;
  references?: unknown;
  /** W3 — research skill used for this turn */
  skill?: string | null;
  metadata?: Record<string, unknown>;
};

/**
 * Normalize a persisted/streamed chat message into ExplainableChatViewModel.
 * Does not invent reasoning, confidence, or workspace references.
 */
export function mapExplainableChat(
  message: ChatMessageLike | null | undefined,
  opts?: { fileId?: number },
): ExplainableChatViewModel | null {
  if (message == null || typeof message !== "object") return null;

  const role = asString(message.role) ?? "assistant";
  const answer =
    (typeof message.answer === "string" ? message.answer : undefined) ??
    (typeof message.content === "string" ? message.content : "") ??
    "";
  const reasoning = asString(message.reasoning ?? undefined);
  const confidence = asNumber(message.confidence ?? undefined);
  const warnings = asStringArray(message.warnings);

  const references: WorkspaceReference[] = [];
  if (Array.isArray(message.references)) {
    message.references.forEach((r, i) => {
      const mapped = mapWorkspaceReference(r, i, opts?.fileId);
      if (mapped) references.push(mapped);
    });
  }

  const metadata: Record<string, unknown> = { ...(message.metadata ?? {}) };
  if (Array.isArray(message.sources) && message.sources.length) {
    metadata.webSources = message.sources
      .filter((s) => s && (s.url || s.title))
      .map((s) => ({
        title: s.title ?? "",
        url: s.url ?? "",
        snippet: s.snippet,
      }));
  }
  const skill = asString(message.skill ?? undefined);
  if (skill) metadata.skill = skill;

  return {
    id: message.id != null ? String(message.id) : `msg:${role}`,
    role,
    answer,
    reasoning,
    confidence,
    warnings,
    references,
    metadata,
  };
}

export type WorkspaceRailInput = {
  fileId: number;
  structure?: DocumentUnderstandingView | null;
  classification?: ClassificationViewModel | null;
  entities?: EntitiesViewModel | null;
  evidence?: EvidenceViewModel | null;
  graph?: KnowledgeGraphViewModel | null;
};

const MONTH =
  "January|February|March|April|May|June|July|August|September|October|November|December";

/** Drop front-matter / footnote noise that pollutes the chat rail. */
export function isUsefulStructureHeading(
  heading: string,
  sectionType?: string,
): boolean {
  const h = heading.trim();
  if (h.length < 3 || h.length > 90) return false;
  if (new RegExp(`^\\d{1,2}\\s+(${MONTH})\\b`, "i").test(h)) return false;
  if (/^\d{4}[-/]\d{1,2}[-/]\d{1,2}/.test(h)) return false;
  if (/contributed equally/i.test(h)) return false;
  if (/^these authors\b/i.test(h)) return false;
  if (/corresponding author/i.test(h)) return false;
  if (/^keywords?:?\s*$/i.test(h)) return false;
  if (/^acknowledg(e)?ments?$/i.test(h)) return false;
  if (/^references$/i.test(h)) return false;
  if (/^supplementary/i.test(h)) return false;
  if (sectionType && !/^(unknown|other|misc)?$/i.test(sectionType)) return true;
  if (/^\d+(\.\d+)*\.?\s+\S/.test(h)) return true;
  if (
    /^(introduction|methods?|materials|results?|discussion|conclusion|abstract|background|methods and materials)\b/i.test(
      h,
    )
  ) {
    return true;
  }
  return h.length >= 10 && h.length <= 72;
}

function truncateLabel(label: string, max: number): string {
  const t = label.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1).trimEnd()}…`;
}

/**
 * Build navigable WorkspaceReferences from already-normalized M5–M9 view models.
 * Chat orchestration only — does not call domain extractors or invent facts.
 */
export function buildWorkspaceRail(input: WorkspaceRailInput): WorkspaceReference[] {
  const { fileId } = input;
  const refs: WorkspaceReference[] = [];

  const structure = input.structure;
  if (structure?.sections?.length) {
    const useful = structure.sections.filter((s) =>
      isUsefulStructureHeading(s.heading, s.sectionType),
    );
    for (const section of useful.slice(0, 5)) {
      const refId = structureSectionRefId(section);
      refs.push({
        id: `rail:${refId}`,
        kind: "structure.section",
        refId,
        label: truncateLabel(section.heading, 42),
        tab: "structure",
        href: workspaceHref(fileId, "structure", refId),
        metadata: section.sectionType ? { sectionType: section.sectionType } : undefined,
      });
    }
  }

  const classification = input.classification;
  if (classification?.decisions?.length) {
    for (const d of classification.decisions) {
      if (!d.label) continue;
      refs.push({
        id: `rail:classification:${d.family}`,
        kind: "classification.decision",
        refId: d.family,
        label: `${d.familyTitle}: ${d.displayLabel ?? d.label}`,
        tab: "classification",
        href: workspaceHref(fileId, "classification", d.family),
        metadata: { label: d.label, confidence: d.confidence },
      });
    }
  }

  const entities = input.entities;
  if (entities && !entities.skipped) {
    const items = [
      ...entities.groups.clinicalEntities.flatMap((g) => g.items),
      ...entities.groups.pico.interventions,
      ...entities.groups.pico.outcomes,
    ].slice(0, 6);
    for (const item of items) {
      refs.push({
        id: `rail:${item.key}`,
        kind: "entity",
        refId: item.key,
        label: truncateLabel(item.displayName, 36),
        tab: "entities",
        href: workspaceHref(fileId, "entities", item.key),
        metadata: { category: item.category, confidence: item.confidence },
      });
    }
  }

  const evidence = input.evidence;
  if (evidence && !evidence.skipped) {
    for (const fw of evidence.frameworks.slice(0, 3)) {
      refs.push({
        id: `rail:${fw.key}`,
        kind: "evidence.framework",
        refId: fw.key,
        label: truncateLabel(
          `${fw.displayName}${fw.displayGrade ? `: ${fw.displayGrade}` : ""}`,
          36,
        ),
        tab: "evidence",
        href: workspaceHref(fileId, "evidence", fw.key),
        metadata: { framework: fw.framework, confidence: fw.confidence },
      });
    }
    for (const o of evidence.outcomeGrades.slice(0, 3)) {
      refs.push({
        id: `rail:${o.key}`,
        kind: "evidence.outcome",
        refId: o.key,
        label: truncateLabel(o.outcomeName, 36),
        tab: "evidence",
        href: workspaceHref(fileId, "evidence", o.key),
        metadata: { grade: o.gradeValue, confidence: o.confidence },
      });
    }
  }

  const graph = input.graph;
  if (graph && !graph.skipped) {
    for (const node of graph.nodes.slice(0, 6)) {
      const refId = graphNodeRefId(node);
      refs.push({
        id: `rail:graph:${refId}`,
        kind: "graph.node",
        refId,
        label: truncateLabel(node.label, 36),
        tab: "graph",
        href: workspaceHref(fileId, "graph", refId),
        metadata: {
          type: node.type,
          category: node.category,
          nodeId: node.id,
          sourceEntityId: node.sourceEntityId,
          key: node.key,
        },
      });
    }
  }

  return refs;
}

export function groupWorkspaceReferences(
  refs: WorkspaceReference[],
): Record<WorkspaceTab, WorkspaceReference[]> {
  const groups: Record<WorkspaceTab, WorkspaceReference[]> = {
    structure: [],
    classification: [],
    entities: [],
    evidence: [],
    graph: [],
  };
  for (const r of refs) {
    groups[r.tab].push(r);
  }
  return groups;
}
