import { describe, it, expect } from "vitest";
import { humanizeEvidenceSkipReason, mapEvidence } from "./evidence";
import { cleanMarkdownArtifacts, humanizeEnumKey, normalizeFrameworkId } from "./shared";
import type { PhaseResult } from "@/features/pipeline";

const SAMPLE: PhaseResult = {
  skipped: false,
  reasoning: null,
  overall_grade: {
    grade_type: "aggregate",
    grade_value: "high",
    grade_description: "Aggregated evidence quality \\(weighted\\_average\\): high",
    confidence: 0.53,
    framework: "unknown",
    prerequisites_used: [],
    rationale: [{ reasoning: "weighted\\_average across frameworks", rule_applied: "weighted_average" }],
    evidence: [],
  },
  study_quality: "high",
  framework_results: {
    "GradingFramework.GRADE": {
      framework: "grade",
      grade: { grade_value: "high", grade_description: "GRADE high", confidence: 0.56, framework: "grade" },
      grade_result: {
        evidence_quality: "high",
        recommendation_strength: "strong",
        downgrade_factors: [],
        upgrade_factors: [],
        initial_quality: "high",
        final_quality: "high",
      },
      confidence: 0.56,
      evidence: [],
    },
    "GradingFramework.OXFORD": {
      framework: "oxford",
      grade: { grade_value: "1", confidence: 0.5, framework: "oxford" },
      grade_result: null,
      confidence: 0.5,
      evidence: [],
    },
  },
  outcome_grades: {
    "Primary outcome at 12 weeks": {
      outcome_name: "Primary outcome at 12 weeks",
      grade: { grade_type: "aggregate", grade_value: "high" },
      confidence: 0.53,
      evidence: [],
    },
    mortality: {
      outcome_name: "mortality",
      grade: { grade_value: "high" },
      confidence: 0.53,
      evidence: [],
    },
  },
  risk_of_bias: {
    overall_risk: "unclear",
    domains: {
      "BiasType.RANDOMIZATION": {
        risk_level: "unclear",
        support_text: "no randomization method described",
        evidence: null,
      },
    },
    assessment_tool: "rob2",
    confidence: 0.4,
    evidence: [],
  },
  consistency: {
    consistency_level: "unavailable",
    applicable: false,
    confidence: 0,
    findings: [],
    evidence: [],
  },
  precision: {
    precision_score: 0.6,
    precision_level: "moderate",
    effect_size: { measure_type: "mean_difference", value: 1.0 },
    confidence_interval: { lower: 0.5, upper: 1.9, level: 0.95 },
    sample_size: null,
    confidence: 0.6,
    evidence: [],
  },
  directness: {
    directness_score: 0.52,
    directness_level: "moderately_direct",
    population_match: 0,
    intervention_match: 0.7,
    confidence: 0.5,
    evidence: [],
  },
  publication_bias: {
    risk_level: "unknown",
    applicable: false,
    confidence: 0,
    evidence: [],
  },
  reporting_quality: {
    reporting_quality_score: 60,
    reporting_guideline: "consort",
    missing_items: ["sample_size_reported"],
    confidence: 0.5,
    evidence: [],
  },
  confidence: {
    overall: 0.53,
    components: { evidence_support: 0 },
    formula: "…",
  },
  warnings: [],
  errors: [],
  pipeline_version: "1.0.0",
};

describe("evidence mapper helpers", () => {
  it("cleans markdown artifacts", () => {
    expect(cleanMarkdownArtifacts("weighted\\_average \\(x\\)")).toBe("weighted_average (x)");
  });

  it("normalizes framework and bias keys", () => {
    expect(normalizeFrameworkId("GradingFramework.GRADE")).toBe("grade");
    expect(normalizeFrameworkId("oxford")).toBe("oxford");
    expect(humanizeEnumKey("BiasType.RANDOMIZATION")).toBe("Randomization");
  });
});

describe("mapEvidence", () => {
  it("returns null for non-objects", () => {
    expect(mapEvidence(null)).toBeNull();
  });

  it("normalizes frameworks and outcome grades without inventing applicability", () => {
    const view = mapEvidence(SAMPLE)!;
    expect(view.frameworks.map((f) => f.framework)).toEqual(["grade", "oxford"]);
    expect(view.frameworks[0].displayGrade).toBe("High");
    expect(view.frameworks[1].displayGrade).toBe("1");
    expect(view.outcomeGrades.map((o) => o.outcomeName).sort()).toEqual(
      ["Primary outcome at 12 weeks", "mortality"].sort(),
    );
    expect(view.outcomeGrades).toHaveLength(2);
    expect(view.overallGrade?.description).toBe(
      "Aggregated evidence quality (weighted_average): high",
    );
    expect(view.summaryConfidence).toBe(0.53);
    expect(view.studyQuality).toBe("high");
  });

  it("humanizes RoB domains and hides unavailable assessments", () => {
    const view = mapEvidence(SAMPLE)!;
    expect(view.assessments.riskOfBias?.domains[0].name).toBe("Randomization");
    expect(view.assessments.consistency).toBeUndefined();
    expect(view.assessments.publicationBias).toBeUndefined();
    expect(view.assessments.precision?.confidenceIntervalLabel).toContain("0.5–1.9");
    expect(view.assessments.reportingQuality?.guideline).toBe("consort");
  });

  it("handles null publication_bias and skipped Ready content", () => {
    const view = mapEvidence({
      skipped: true,
      reasoning: "evidence grading not required (routing profile does not include evidence_grading)",
      overall_grade: { grade_value: "", confidence: 0 },
      study_quality: "unknown",
      framework_results: {},
      outcome_grades: {},
      publication_bias: null,
      confidence: { overall: 0, components: {}, formula: "" },
      warnings: ["note"],
      errors: [],
      pipeline_version: "1.0.0",
    })!;
    expect(view.skipped).toBe(true);
    expect(view.hasContent).toBe(true);
    expect(view.assessments.publicationBias).toBeUndefined();
    expect(view.skipTitle).toBe("No formal evidence grade");
    expect(view.skipReason).toMatch(/narrative reviews/i);
    expect(view.skipReason).not.toMatch(/routing profile|evidence_grading/i);
  });
});

describe("humanizeEvidenceSkipReason", () => {
  it("never surfaces routing-profile jargon", () => {
    const copy = humanizeEvidenceSkipReason(
      "evidence grading not required (routing profile does not include evidence_grading)",
    );
    expect(copy.title).toBe("No formal evidence grade");
    expect(copy.detail).not.toMatch(/routing profile|evidence_grading/i);
  });
});
