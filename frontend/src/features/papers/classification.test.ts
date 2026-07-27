import { describe, it, expect } from "vitest";
import {
  mapClassification,
  mapAnalysisSummary,
  formatClassificationLabel,
  formatConfidence,
} from "./mappers/classification";
import type { PhaseResult } from "@/features/pipeline";

const SAMPLE_CLASSIFICATION: PhaseResult = {
  document_type: {
    label: "research_article",
    confidence: 0.5555555555555555,
    evidence: ["2/6 DocumentType.RESEARCH_ARTICLE keyword(s) matched"],
    reasoning: "Classified as 'research_article' with confidence 0.56.",
  },
  domain: {
    label: "medicine",
    confidence: 0.35714285714285715,
    evidence: ["5/14 ScientificDomain.MEDICINE keyword(s) matched"],
    reasoning: null,
  },
  study_design: {
    label: "rct",
    confidence: 0.3333333333333333,
    evidence: [],
    reasoning: null,
  },
  reporting_guideline: {
    label: "consort",
    confidence: 0.55,
    evidence: ["study_design classified as 'rct'"],
    reasoning: "Classified as 'consort'.",
  },
  detected_keywords: ["patient", "clinical", "randomized controlled trial"],
  candidate_labels: {
    "document_type.research_article": 0.5555555555555555,
    "document_type.survey": 0.1,
    "domain.medicine": 0.35714285714285715,
    "study_design.rct": 0.3333333333333333,
  },
  warnings: [],
  processing_time_ms: 1.14,
  pipeline_version: "1.0.0",
};

const SAMPLE_CONTEXT: PhaseResult = {
  document_profile: {
    document_type: "research_article",
    domain: "medicine",
    study_design: "rct",
    reporting_guideline: "consort",
    intended_audience: "research",
    complexity_level: "simple",
    confidence: 0.4,
    evidence: [],
  },
  analysis_profile: {
    analysis_types: ["statistical_review", "bias_assessment"],
    readiness_score: 0.9,
    readiness_level: "partially_ready",
    limitations: ["Missing limitations section"],
    confidence: 0.3,
  },
  routing_profile: {
    primary_routing: "clinical_trial",
    module_pipeline: ["medical_understanding", "evidence_grading"],
    confidence: 0.4,
  },
  quality_profile: {
    reliability_score: 0.62,
    reliability_level: "fair",
    caveats: [],
  },
  confidence: {
    overall: 0.45,
    document_profile: 0.4,
    section_profile: 0.6,
    analysis_profile: 0.3,
    routing_profile: 0.4,
    prompt_profile: 0.4,
  },
  warnings: [],
  processing_time_ms: 0.13,
  pipeline_version: "1.0.0",
};

describe("formatClassificationLabel / formatConfidence", () => {
  it("formats known acronyms and snake_case", () => {
    expect(formatClassificationLabel("rct")).toBe("RCT");
    expect(formatClassificationLabel("research_article")).toBe("Research Article");
    expect(formatClassificationLabel("ai_ml")).toBe("AI/ML");
  });

  it("formats 0–1 confidence from the backend float only", () => {
    expect(formatConfidence(0.555)).toBe("56%");
    expect(formatConfidence(undefined)).toBeUndefined();
  });
});

describe("mapClassification", () => {
  it("returns null for non-objects", () => {
    expect(mapClassification(null)).toBeNull();
    expect(mapClassification(undefined)).toBeNull();
  });

  it("maps four decisions, candidates, keywords without inventing values", () => {
    const view = mapClassification(SAMPLE_CLASSIFICATION)!;
    expect(view.hasContent).toBe(true);
    expect(view.decisions).toHaveLength(4);
    expect(view.decisions[0]).toMatchObject({
      family: "document_type",
      label: "research_article",
      displayLabel: "Research Article",
      confidence: 0.5555555555555555,
      reasoning: "Classified as 'research_article' with confidence 0.56.",
    });
    expect(view.decisions[1].label).toBe("medicine");
    expect(view.decisions[2].displayLabel).toBe("RCT");
    expect(view.decisions[3].label).toBe("consort");
    expect(view.keywords).toEqual(["patient", "clinical", "randomized controlled trial"]);
    expect(view.candidates.map((c) => c.key)).toEqual([
      "document_type.research_article",
      "domain.medicine",
      "study_design.rct",
      "document_type.survey",
    ]);
    expect(view.pipelineVersion).toBe("1.0.0");
    expect(view.analysisSummary).toBeNull();
  });

  it("treats all-unknown results with warnings as Ready content", () => {
    const view = mapClassification({
      document_type: { label: "unknown", confidence: 0, evidence: [], reasoning: null },
      domain: { label: "unknown", confidence: 0, evidence: [], reasoning: null },
      study_design: { label: "unknown", confidence: 0, evidence: [], reasoning: null },
      reporting_guideline: { label: "unknown", confidence: 0, evidence: [], reasoning: null },
      detected_keywords: [],
      candidate_labels: {},
      warnings: ["document has no title"],
      processing_time_ms: 0.2,
      pipeline_version: "1.0.0",
    })!;
    expect(view.hasContent).toBe(true);
    expect(view.warnings).toEqual(["document has no title"]);
    expect(view.decisions.every((d) => d.label === "unknown")).toBe(true);
  });

  it("attaches slim analysis summary when context is present", () => {
    const view = mapClassification(SAMPLE_CLASSIFICATION, SAMPLE_CONTEXT)!;
    expect(view.analysisSummary).toEqual({
      audience: "research",
      readiness: "partially_ready",
      routing: "clinical_trial",
      reliability: "fair",
      overallConfidence: 0.45,
      hasContent: true,
    });
  });

  it("omits summary when analysis_context has no displayable strip fields", () => {
    const view = mapClassification(SAMPLE_CLASSIFICATION, {
      document_profile: { complexity_level: "simple" },
      analysis_profile: { analysis_types: ["statistical_review"] },
      routing_profile: { module_pipeline: ["medical_understanding"] },
      quality_profile: { caveats: ["x"] },
      confidence: {},
      warnings: ["ignored for strip"],
    })!;
    expect(view.analysisSummary).toBeNull();
  });
});

describe("mapAnalysisSummary", () => {
  it("exposes only audience, readiness, routing, reliability, overall confidence", () => {
    const summary = mapAnalysisSummary(SAMPLE_CONTEXT)!;
    expect(Object.keys(summary).sort()).toEqual(
      [
        "audience",
        "hasContent",
        "overallConfidence",
        "readiness",
        "reliability",
        "routing",
      ].sort(),
    );
  });
});
