/**
 * Knowledge Graph tab mapper — Phase 1.7 `knowledge_graph`.
 * Pattern: mapKnowledgeGraph(phase) → KnowledgeGraphViewModel → PaperKnowledgeGraphTab
 *
 * API shape is to_jsonable(KnowledgeGraph): node_id / source_node_id / evidence_references.
 * Do not map JSONSerializer fields (id / source / evidence).
 */

import type { PhaseResult } from "@/features/pipeline";
import {
  asNumber,
  asString,
  asStringArray,
  asBoolean,
  formatConfidence,
  formatLabel,
  isRecord,
  normalizeEvidence,
  normalizeFrameworkId,
} from "./shared";

export { formatConfidence, formatLabel };

/** Broad filter categories derived from node_type (not invented clinical labels). */
export const GRAPH_CATEGORIES = [
  "study",
  "clinical",
  "pico",
  "evidence",
  "other",
] as const;

export type GraphCategory = (typeof GRAPH_CATEGORIES)[number];

const CLINICAL_TYPES = new Set([
  "disease",
  "condition",
  "symptom",
  "medication",
  "treatment",
  "procedure",
  "biomarker",
  "lab_test",
  "demographic",
  "location",
  "timepoint",
]);

const PICO_TYPES = new Set(["population", "intervention", "comparator", "outcome"]);
const STUDY_TYPES = new Set(["study", "author", "organization", "journal"]);
const EVIDENCE_TYPES = new Set([
  "evidence_claim",
  "statistical_result",
  "grade_quality",
  "prompt_component",
]);

export function categoryForNodeType(nodeType: string): GraphCategory {
  const t = nodeType.toLowerCase();
  if (STUDY_TYPES.has(t)) return "study";
  if (PICO_TYPES.has(t)) return "pico";
  if (EVIDENCE_TYPES.has(t)) return "evidence";
  if (CLINICAL_TYPES.has(t)) return "clinical";
  return "other";
}

export type GraphNodeView = {
  /** Backend node_id — used to wire edges within this payload. */
  id: string;
  /** Render key (not durable across re-analyses). */
  key: string;
  label: string;
  type: string;
  category: GraphCategory;
  confidence?: number;
  metadata: Record<string, string | number | boolean>;
  evidenceCount: number;
  properties: Record<string, string | number | boolean>;
  sourceEntityId?: string;
};

export type GraphEdgeView = {
  id: string;
  key: string;
  source: string;
  target: string;
  relationship: string;
  confidence?: number;
  direction?: string;
  inferred?: boolean;
  metadata: Record<string, string | number | boolean>;
  evidenceCount: number;
};

export type GraphStatisticsView = {
  totalNodes?: number;
  totalEdges?: number;
  averageDegree?: number;
  maxDegree?: number;
  connectedComponents?: number;
  diameter?: number;
  clusteringCoefficient?: number;
  nodeTypeCounts: { type: string; count: number }[];
  edgeTypeCounts: { type: string; count: number }[];
};

export type GraphSummaryView = {
  nodeCount: number;
  edgeCount: number;
  connectedComponents?: number;
  averageConfidence?: number;
  overallConfidence?: number;
};

export type KnowledgeGraphViewModel = {
  skipped: boolean;
  skipReason?: string;
  hasContent: boolean;
  summary: GraphSummaryView;
  nodes: GraphNodeView[];
  edges: GraphEdgeView[];
  statistics: GraphStatisticsView;
  warnings: string[];
  errors: string[];
  graphId?: string;
  pipelineVersion?: string;
};

function normalizeTypeToken(raw: string): string {
  // "NodeType.MEDICATION" / "EdgeType.TREATS" / "medication"
  return normalizeFrameworkId(raw);
}

function flattenPropertyValue(
  v: unknown,
): string | number | boolean | undefined {
  if (typeof v === "string") return v.trim() ? v : undefined;
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "boolean") return v;
  if (Array.isArray(v)) {
    const parts = v.filter((x): x is string => typeof x === "string" && x.trim().length > 0);
    return parts.length ? parts.join(", ") : undefined;
  }
  return undefined;
}

function mapProperties(raw: unknown): Record<string, string | number | boolean> {
  if (!isRecord(raw)) return {};
  const out: Record<string, string | number | boolean> = {};
  for (const [k, v] of Object.entries(raw)) {
    const flat = flattenPropertyValue(v);
    if (flat === undefined) continue;
    out[k] = flat;
  }
  return out;
}

function mapCountDict(raw: unknown): { type: string; count: number }[] {
  if (!isRecord(raw)) return [];
  const out: { type: string; count: number }[] = [];
  for (const [k, v] of Object.entries(raw)) {
    const count = asNumber(v);
    if (count == null) continue;
    out.push({ type: normalizeTypeToken(k), count });
  }
  out.sort((a, b) => b.count - a.count || a.type.localeCompare(b.type));
  return out;
}

function mapNodes(raw: unknown): GraphNodeView[] {
  if (!Array.isArray(raw)) return [];
  const out: GraphNodeView[] = [];
  raw.forEach((item, index) => {
    if (!isRecord(item)) return;
    const id = asString(item.node_id);
    const label = asString(item.label);
    if (!id || !label) return;
    const typeRaw = asString(item.node_type) ?? "unknown";
    const type = normalizeTypeToken(typeRaw);
    const category = categoryForNodeType(type);
    const sourceEntityId = asString(item.source_entity_id);
    const evidence = normalizeEvidence(item.evidence_references);
    const properties = mapProperties(item.properties);
    const confidence = asNumber(item.confidence);

    const metadata: Record<string, string | number | boolean> = { ...properties };
    if (sourceEntityId) metadata.sourceEntityId = sourceEntityId;

    out.push({
      id,
      key: `node:${type}:${sourceEntityId ?? label}:${index}`,
      label,
      type,
      category,
      confidence,
      metadata,
      evidenceCount: evidence.length,
      properties,
      sourceEntityId,
    });
  });
  return out;
}

function mapEdges(raw: unknown, validNodeIds: Set<string>): GraphEdgeView[] {
  if (!Array.isArray(raw)) return [];
  const out: GraphEdgeView[] = [];
  raw.forEach((item, index) => {
    if (!isRecord(item)) return;
    const id = asString(item.edge_id);
    const source = asString(item.source_node_id);
    const target = asString(item.target_node_id);
    if (!id || !source || !target) return;
    // Drop dangling edges that don't resolve in this payload
    if (!validNodeIds.has(source) || !validNodeIds.has(target)) return;

    const relationship = normalizeTypeToken(asString(item.edge_type) ?? asString(item.label) ?? "related_to");
    const props = mapProperties(item.properties);
    const inferred = asBoolean(props.inferred) ?? asBoolean(item.properties && isRecord(item.properties) ? item.properties.inferred : undefined);
    const evidence = normalizeEvidence(item.evidence_references);
    const confidence = asNumber(item.confidence);
    const direction = asString(item.direction);

    const metadata: Record<string, string | number | boolean> = { ...props };
    if (inferred) metadata.inferred = true;

    out.push({
      id,
      key: `edge:${relationship}:${source}:${target}:${index}`,
      source,
      target,
      relationship,
      confidence,
      direction,
      inferred: inferred === true ? true : undefined,
      metadata,
      evidenceCount: evidence.length,
    });
  });
  return out;
}

function errorMessages(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  const out: string[] = [];
  for (const item of raw) {
    if (typeof item === "string" && item.trim()) {
      out.push(item);
      continue;
    }
    if (!isRecord(item)) continue;
    const msg = asString(item.message);
    const component = asString(item.component);
    if (msg && component) out.push(`${component}: ${msg}`);
    else if (msg) out.push(msg);
  }
  return out;
}

function meanConfidence(nodes: GraphNodeView[], edges: GraphEdgeView[]): number | undefined {
  const vals = [
    ...nodes.map((n) => n.confidence).filter((n): n is number => n != null),
    ...edges.map((e) => e.confidence).filter((n): n is number => n != null),
  ];
  if (!vals.length) return undefined;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

/**
 * Adapt opaque knowledge_graph phase JSON into KnowledgeGraphViewModel.
 */
export function mapKnowledgeGraph(
  phase: PhaseResult | null | undefined,
): KnowledgeGraphViewModel | null {
  if (!phase || !isRecord(phase)) return null;

  const warnings = asStringArray(phase.warnings);
  const errors = errorMessages(phase.errors);
  const skippedFlag = phase.skipped === true;
  const upstreamSkipWarning = warnings.find((w) => /skipped/i.test(w));
  const skipReason = asString(phase.reasoning) ?? (skippedFlag ? upstreamSkipWarning : undefined);

  const nodes = mapNodes(phase.nodes);
  const validIds = new Set(nodes.map((n) => n.id));
  const edges = mapEdges(phase.edges, validIds);

  const statsRaw = isRecord(phase.statistics) ? phase.statistics : {};
  const confidenceObj = isRecord(phase.confidence) ? phase.confidence : {};
  const overallConfidence = asNumber(confidenceObj.overall_confidence);

  const statistics: GraphStatisticsView = {
    totalNodes: asNumber(statsRaw.total_nodes) ?? nodes.length,
    totalEdges: asNumber(statsRaw.total_edges) ?? edges.length,
    averageDegree: asNumber(statsRaw.average_degree),
    maxDegree: asNumber(statsRaw.max_degree),
    connectedComponents: asNumber(statsRaw.connected_components),
    diameter: asNumber(statsRaw.diameter) ?? undefined,
    clusteringCoefficient: asNumber(statsRaw.clustering_coefficient) ?? undefined,
    nodeTypeCounts: mapCountDict(statsRaw.node_type_counts),
    edgeTypeCounts: mapCountDict(statsRaw.edge_type_counts),
  };

  const summary: GraphSummaryView = {
    nodeCount: statistics.totalNodes ?? nodes.length,
    edgeCount: statistics.totalEdges ?? edges.length,
    connectedComponents: statistics.connectedComponents,
    averageConfidence: meanConfidence(nodes, edges),
    overallConfidence,
  };

  // Phase present ⇒ Ready (including empty graphs / upstream-skip thin graphs)
  const hasContent = true;

  return {
    skipped: skippedFlag,
    skipReason,
    hasContent,
    summary,
    nodes,
    edges,
    statistics,
    warnings,
    errors,
    graphId: asString(phase.graph_id),
    pipelineVersion: asString(phase.pipeline_version),
  };
}

export type GraphFilterState = {
  query: string;
  categories: Set<GraphCategory> | null; // null = all
  relationships: Set<string> | null;
  minConfidence: number | null;
};

export function filterKnowledgeGraph(
  view: KnowledgeGraphViewModel,
  filter: GraphFilterState,
): { nodes: GraphNodeView[]; edges: GraphEdgeView[]; matchedNodeIds: Set<string> } {
  const q = filter.query.trim().toLowerCase();

  const matchedNodeIds = new Set<string>();
  let nodes = view.nodes.filter((n) => {
    if (filter.categories && !filter.categories.has(n.category)) return false;
    if (filter.minConfidence != null && (n.confidence == null || n.confidence < filter.minConfidence)) {
      return false;
    }
    if (!q) return true;
    const hay = [
      n.label,
      n.type,
      n.sourceEntityId ?? "",
      ...Object.values(n.metadata).map(String),
      ...Object.values(n.properties).map(String),
    ]
      .join(" ")
      .toLowerCase();
    const hit = hay.includes(q);
    if (hit) matchedNodeIds.add(n.id);
    return hit;
  });

  // When searching, keep unmatched nodes that are endpoints of matching edges by relationship name
  let edges = view.edges.filter((e) => {
    if (filter.relationships && !filter.relationships.has(e.relationship)) return false;
    if (filter.minConfidence != null && (e.confidence == null || e.confidence < filter.minConfidence)) {
      return false;
    }
    if (!q) return true;
    if (e.relationship.toLowerCase().includes(q) || e.id.toLowerCase().includes(q)) {
      matchedNodeIds.add(e.source);
      matchedNodeIds.add(e.target);
      return true;
    }
    return matchedNodeIds.has(e.source) || matchedNodeIds.has(e.target);
  });

  if (q) {
    const keep = new Set<string>();
    for (const e of edges) {
      keep.add(e.source);
      keep.add(e.target);
    }
    for (const id of matchedNodeIds) keep.add(id);
    nodes = view.nodes.filter((n) => keep.has(n.id));
    // re-filter nodes by category/confidence after expand
    nodes = nodes.filter((n) => {
      if (filter.categories && !filter.categories.has(n.category)) return false;
      if (filter.minConfidence != null && (n.confidence == null || n.confidence < filter.minConfidence)) {
        return false;
      }
      return true;
    });
    const nodeIds = new Set(nodes.map((n) => n.id));
    edges = edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));
  } else {
    const nodeIds = new Set(nodes.map((n) => n.id));
    edges = edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));
  }

  return { nodes, edges, matchedNodeIds: q ? matchedNodeIds : new Set() };
}

export function uniqueRelationships(view: KnowledgeGraphViewModel): string[] {
  return [...new Set(view.edges.map((e) => e.relationship))].sort();
}

export function uniqueCategories(view: KnowledgeGraphViewModel): GraphCategory[] {
  return GRAPH_CATEGORIES.filter((c) => view.nodes.some((n) => n.category === c));
}
