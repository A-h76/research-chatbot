import { describe, it, expect } from "vitest";
import {
  mapExplainableChat,
  buildWorkspaceRail,
  workspaceHref,
  groupWorkspaceReferences,
  resolveGraphNodeId,
} from "./chat";
import type { EntitiesViewModel } from "./entities";
import type { EvidenceViewModel } from "./evidence";
import type { KnowledgeGraphViewModel } from "./graph";
import type { ClassificationViewModel } from "./classification";
import type { DocumentUnderstandingView } from "./structure";

describe("mapExplainableChat", () => {
  it("returns null for non-objects", () => {
    expect(mapExplainableChat(null)).toBeNull();
    expect(mapExplainableChat(undefined)).toBeNull();
  });

  it("maps live chat message fields without inventing reasoning or refs", () => {
    const view = mapExplainableChat(
      {
        id: 42,
        role: "assistant",
        content: "According to the methods section…",
        sources: [{ title: "Web", url: "https://example.com", snippet: "…" }],
      },
      { fileId: 9 },
    )!;
    expect(view.answer).toBe("According to the methods section…");
    expect(view.reasoning).toBeUndefined();
    expect(view.confidence).toBeUndefined();
    expect(view.references).toEqual([]);
    expect(view.metadata.webSources).toEqual([
      { title: "Web", url: "https://example.com", snippet: "…" },
    ]);
  });

  it("maps W4 grounding confidence and warnings", () => {
    const view = mapExplainableChat(
      {
        id: 7,
        role: "assistant",
        content: "Grounded claim from the paper.",
        confidence: 0.81,
        warnings: ["Partial grounding — verify claims"],
        skill: "synthesize",
      },
      { fileId: 3 },
    )!;
    expect(view.confidence).toBe(0.81);
    expect(view.warnings).toEqual(["Partial grounding — verify claims"]);
  });

  it("maps W1 Trust Chat passage references from the live contract", () => {
    const view = mapExplainableChat(
      {
        id: 99,
        role: "assistant",
        content: "Kupffer cells regulate immunity.",
        references: [
          {
            id: "passage:7:passage:chunk:101:0",
            kind: "passage",
            refId: "passage:chunk:101",
            label: "p. 4 · Discussion",
            tab: "structure",
            href: "/papers/7?tab=structure&ref=passage%3Achunk%3A101",
            metadata: { file_id: 7, page: 4 },
          },
        ],
      },
      { fileId: 7 },
    )!;
    expect(view.references).toHaveLength(1);
    expect(view.references[0].kind).toBe("passage");
    expect(view.references[0].label).toContain("p. 4");
    expect(view.references[0].href).toContain("/papers/7");
  });

  it("passes through structured references only when present and valid", () => {
    const view = mapExplainableChat(
      {
        role: "assistant",
        content: "Answer",
        references: [
          { kind: "entity", refId: "clinical_entities:drug:metformin:0", label: "Metformin" },
          { kind: "nope", refId: "x" },
          { kind: "entity" },
        ],
      },
      { fileId: 9 },
    )!;
    expect(view.references).toHaveLength(1);
    expect(view.references[0]).toMatchObject({
      kind: "entity",
      refId: "clinical_entities:drug:metformin:0",
      tab: "entities",
      href: "/papers/9?tab=entities&ref=clinical_entities%3Adrug%3Ametformin%3A0",
    });
  });
});

describe("buildWorkspaceRail", () => {
  it("builds navigable refs from existing view models using stable ids", () => {
    const structure = {
      sections: [{ heading: "Methods", sectionType: "methods" }],
      references: [],
      authors: [],
      warnings: [],
      errors: [],
      quality: {},
      scientificStructure: null,
      methodologyProfile: null,
      statisticsProfile: null,
      limitationsNoveltyProfile: null,
      qualityAssessment: null,
      hasContent: true,
    } as unknown as DocumentUnderstandingView;

    const classification = {
      decisions: [
        {
          family: "domain",
          familyTitle: "Domain",
          label: "medicine",
          displayLabel: "Medicine",
          confidence: 0.8,
          evidence: [],
        },
      ],
      candidates: [],
      keywords: [],
      warnings: [],
      analysisSummary: null,
      hasContent: true,
    } as ClassificationViewModel;

    const entities = {
      skipped: false,
      warnings: [],
      errors: [],
      summary: {
        clinicalEntityCount: 1,
        interventionCount: 0,
        populationCount: 0,
        outcomeCount: 0,
      },
      groups: {
        clinicalEntities: [
          {
            entityType: "drug",
            displayType: "Drug",
            items: [
              {
                key: "clinical_entities:drug:Metformin:0",
                displayName: "Metformin",
                category: "drug",
                synonyms: [],
                evidence: [],
                extras: {},
              },
            ],
          },
        ],
        pico: { populations: [], interventions: [], comparators: [], outcomes: [] },
        statistics: [],
        findings: [],
        studyCharacteristics: [],
        temporal: [],
        scientificEntities: [],
      },
      localRelations: [],
      hasContent: true,
    } as unknown as EntitiesViewModel;

    const evidence = {
      skipped: false,
      overallGrade: null,
      frameworks: [
        {
          key: "framework:grade",
          framework: "grade",
          displayName: "GRADE",
          displayGrade: "High",
          downgradeFactors: [],
          upgradeFactors: [],
          evidence: [],
        },
      ],
      outcomeGrades: [],
      assessments: {},
      warnings: [],
      errors: [],
      hasContent: true,
    } as EvidenceViewModel;

    const graph = {
      skipped: false,
      summary: { nodeCount: 1, edgeCount: 0 },
      nodes: [
        {
          id: "uuid-transient",
          key: "node:medication:Metformin:0",
          label: "Metformin",
          type: "medication",
          category: "clinical",
          metadata: {},
          evidenceCount: 0,
          properties: {},
          sourceEntityId: "Metformin",
        },
      ],
      edges: [],
      statistics: { nodeTypeCounts: [], edgeTypeCounts: [] },
      warnings: [],
      errors: [],
      hasContent: true,
    } as KnowledgeGraphViewModel;

    const refs = buildWorkspaceRail({
      fileId: 9,
      structure,
      classification,
      entities,
      evidence,
      graph,
    });

    expect(refs.some((r) => r.kind === "structure.section" && r.tab === "structure")).toBe(true);
    expect(refs.some((r) => r.kind === "classification.decision" && r.refId === "domain")).toBe(
      true,
    );
    expect(refs.some((r) => r.kind === "entity" && r.refId === "clinical_entities:drug:Metformin:0")).toBe(
      true,
    );
    expect(refs.some((r) => r.kind === "evidence.framework" && r.refId === "framework:grade")).toBe(
      true,
    );
    const graphRef = refs.find((r) => r.kind === "graph.node")!;
    expect(graphRef.refId).toBe("source:medication:Metformin");
    expect(graphRef.href).toContain("tab=graph");

    const groups = groupWorkspaceReferences(refs);
    expect(groups.entities.length).toBeGreaterThan(0);
  });

  it("filters front-matter and footnote headings from the structure rail", () => {
    const structure = {
      sections: [
        { heading: "20 January 2026" },
        { heading: "1 These authors contributed equally to this work" },
        { heading: "1. Introduction", sectionType: "introduction" },
        { heading: "2. Origin and heterogeneity of KCs", sectionType: "other" },
      ],
      references: [],
      authors: [],
      warnings: [],
      errors: [],
      quality: {},
      scientificStructure: null,
      methodologyProfile: null,
      statisticsProfile: null,
      limitationsNoveltyProfile: null,
      qualityAssessment: null,
      hasContent: true,
    } as unknown as DocumentUnderstandingView;

    const refs = buildWorkspaceRail({ fileId: 9, structure });
    const labels = refs.filter((r) => r.tab === "structure").map((r) => r.label);
    expect(labels.some((l) => /January|contributed equally/i.test(l ?? ""))).toBe(false);
    expect(labels.some((l) => /Introduction/i.test(l ?? ""))).toBe(true);
  });
});

describe("workspaceHref", () => {
  it("builds paper workspace deep links", () => {
    expect(workspaceHref(9, "evidence", "framework:grade")).toBe(
      "/papers/9?tab=evidence&ref=framework%3Agrade",
    );
  });
});

describe("resolveGraphNodeId", () => {
  it("resolves stable sourceEntityId refs to current node ids", () => {
    const graph = {
      skipped: false,
      summary: { nodeCount: 1, edgeCount: 0 },
      nodes: [
        {
          id: "uuid-new-run",
          key: "node:medication:Metformin:0",
          label: "Metformin",
          type: "medication",
          category: "clinical",
          metadata: {},
          evidenceCount: 0,
          properties: {},
          sourceEntityId: "Metformin",
        },
      ],
      edges: [],
      statistics: { nodeTypeCounts: [], edgeTypeCounts: [] },
      warnings: [],
      errors: [],
      hasContent: true,
    } as KnowledgeGraphViewModel;

    expect(resolveGraphNodeId(graph, "source:medication:Metformin")).toBe("uuid-new-run");
    expect(resolveGraphNodeId(graph, "node:medication:Metformin:0")).toBe("uuid-new-run");
    expect(resolveGraphNodeId(graph, "missing")).toBeNull();
  });
});
