import { describe, it, expect } from "vitest";
import {
  mapKnowledgeGraph,
  filterKnowledgeGraph,
  categoryForNodeType,
} from "./graph";
import type { PhaseResult } from "@/features/pipeline";

const SAMPLE: PhaseResult = {
  graph_id: "g-1",
  skipped: false,
  reasoning: null,
  nodes: [
    {
      node_id: "n-study",
      node_type: "study",
      label: "Metformin Trial",
      properties: { study_design: "rct", year: 2020 },
      evidence_references: [],
      confidence: 0.6,
      source_entity_id: "study:abc",
    },
    {
      node_id: "n-drug",
      node_type: "medication",
      label: "Metformin",
      properties: { entity_type: "drug", synonyms: ["glucophage"] },
      evidence_references: [{ text_snippet: "metformin", confidence: 0.9 }],
      confidence: 0.72,
      source_entity_id: "Metformin",
    },
    {
      node_id: "n-cond",
      node_type: "condition",
      label: "Type 2 Diabetes",
      properties: {},
      evidence_references: [],
      confidence: 0.74,
      source_entity_id: "Type 2 Diabetes",
    },
  ],
  edges: [
    {
      edge_id: "e1",
      source_node_id: "n-drug",
      target_node_id: "n-cond",
      edge_type: "treats",
      label: "treats",
      properties: {},
      direction: "directed",
      evidence_references: [{ text_snippet: "metformin", confidence: 0.9 }],
      confidence: 0.56,
    },
    {
      edge_id: "e2",
      source_node_id: "n-drug",
      target_node_id: "n-cond",
      edge_type: "treats",
      label: "treats",
      properties: { inferred: true },
      direction: "directed",
      evidence_references: [],
      confidence: 0.38,
    },
    {
      edge_id: "e-dangling",
      source_node_id: "n-drug",
      target_node_id: "missing",
      edge_type: "related_to",
      confidence: 0.1,
    },
  ],
  statistics: {
    total_nodes: 3,
    total_edges: 2,
    connected_components: 2,
    average_degree: 1.3,
    node_type_counts: { "NodeType.STUDY": 1, "NodeType.MEDICATION": 1, "NodeType.CONDITION": 1 },
    edge_type_counts: { "EdgeType.TREATS": 2 },
  },
  confidence: {
    overall_confidence: 0.65,
    node_confidence: {},
    edge_confidence: {},
    confidence_distribution: { high: 0.1, medium: 0.5, low: 0.4 },
    formula: "…",
  },
  warnings: [],
  errors: [],
  pipeline_version: "1.0.0",
};

describe("categoryForNodeType", () => {
  it("maps backend node types into filter categories", () => {
    expect(categoryForNodeType("medication")).toBe("clinical");
    expect(categoryForNodeType("population")).toBe("pico");
    expect(categoryForNodeType("study")).toBe("study");
    expect(categoryForNodeType("grade_quality")).toBe("evidence");
  });
});

describe("mapKnowledgeGraph", () => {
  it("returns null for non-objects", () => {
    expect(mapKnowledgeGraph(null)).toBeNull();
  });

  it("normalizes nodes/edges and strips enum count keys", () => {
    const view = mapKnowledgeGraph(SAMPLE)!;
    expect(view.nodes).toHaveLength(3);
    expect(view.nodes[1]).toMatchObject({
      id: "n-drug",
      label: "Metformin",
      type: "medication",
      category: "clinical",
      evidenceCount: 1,
    });
    expect(view.nodes[1].properties.synonyms).toBe("glucophage");
    // dangling edge dropped
    expect(view.edges).toHaveLength(2);
    expect(view.edges[0].relationship).toBe("treats");
    expect(view.edges[1].inferred).toBe(true);
    expect(view.statistics.nodeTypeCounts.map((c) => c.type)).toEqual([
      "condition",
      "medication",
      "study",
    ]);
    expect(view.summary).toMatchObject({
      nodeCount: 3,
      edgeCount: 2,
      connectedComponents: 2,
      overallConfidence: 0.65,
    });
  });

  it("treats empty graphs as Ready content", () => {
    const view = mapKnowledgeGraph({
      graph_id: "g",
      skipped: false,
      nodes: [],
      edges: [],
      statistics: { total_nodes: 0, total_edges: 0, node_type_counts: {}, edge_type_counts: {} },
      confidence: { overall_confidence: 0 },
      warnings: ["medical understanding skipped: not medical"],
      errors: [],
      pipeline_version: "1.0.0",
    })!;
    expect(view.hasContent).toBe(true);
    expect(view.nodes).toEqual([]);
    expect(view.warnings[0]).toMatch(/skipped/i);
  });

  it("does not invent JSONSerializer field names", () => {
    const view = mapKnowledgeGraph({
      nodes: [{ id: "x", type: "study", label: "Bad", evidence: [] }],
      edges: [{ id: "e", source: "x", target: "x", type: "treats" }],
      statistics: {},
      confidence: {},
      warnings: [],
      errors: [],
    })!;
    expect(view.nodes).toEqual([]);
    expect(view.edges).toEqual([]);
  });
});

describe("filterKnowledgeGraph", () => {
  it("filters by query on labels and synonyms metadata", () => {
    const view = mapKnowledgeGraph(SAMPLE)!;
    const { nodes, matchedNodeIds } = filterKnowledgeGraph(view, {
      query: "glucophage",
      categories: null,
      relationships: null,
      minConfidence: null,
    });
    expect(matchedNodeIds.has("n-drug")).toBe(true);
    expect(nodes.some((n) => n.id === "n-drug")).toBe(true);
  });
});
