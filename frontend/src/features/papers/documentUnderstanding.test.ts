import { describe, it, expect } from "vitest";
import { mapStructure, parseDocumentUnderstanding, formatQualityScore } from "./mappers/structure";
import type { PhaseResult } from "@/features/pipeline";

const SAMPLE: PhaseResult = {
  id: "doc-1",
  metadata: {
    title: "A Study of Widgets",
    authors: ["Ada Lovelace", "Alan Turing"],
    journal: "Nature Methods",
    venue: "",
    publication_year: 2024,
    language: "en",
    doi: "10.1000/xyz",
    abstract: "We study widgets.",
  },
  structure: {
    heading_order: ["Introduction", "Methods"],
    raw_headings: {
      Introduction: "Widgets matter.",
      Methods: "We measured things.",
    },
    section_types: {
      Introduction: "introduction",
      Methods: "methods",
    },
    references: [],
  },
  statistics: {
    word_count: 1200,
    page_count: 8,
    section_count: 2,
  },
  quality: {
    extraction_quality: 0.9,
    confidence: 0.85,
    warnings: ["Low figure contrast"],
    errors: [],
  },
};

describe("mapStructure", () => {
  it("returns null for non-objects", () => {
    expect(mapStructure(null)).toBeNull();
    expect(parseDocumentUnderstanding(undefined)).toBeNull();
  });

  it("maps bibliographic and structure fields without inventing values", () => {
    const view = mapStructure(SAMPLE)!;
    expect(view.title).toBe("A Study of Widgets");
    expect(view.authors).toEqual(["Ada Lovelace", "Alan Turing"]);
    expect(view.journal).toBe("Nature Methods");
    expect(view.publicationYear).toBe(2024);
    expect(view.language).toBe("en");
    expect(view.wordCount).toBe(1200);
    expect(view.pageCount).toBe(8);
    expect(view.sections).toHaveLength(2);
    expect(view.sections[0]).toMatchObject({
      heading: "Introduction",
      sectionType: "introduction",
      content: "Widgets matter.",
    });
    expect(view.references).toEqual([]);
    expect(view.warnings).toEqual(["Low figure contrast"]);
    expect(view.quality.extraction_quality).toBe(0.9);
    expect(view.hasContent).toBe(true);
  });

  it("marks empty payloads as no content", () => {
    const view = mapStructure({
      metadata: {},
      structure: {},
      statistics: {},
      quality: {},
    })!;
    expect(view.hasContent).toBe(false);
  });

  it("prefers journal over empty venue for display mapping", () => {
    const view = mapStructure({
      metadata: { venue: "Conference X", journal: null },
      structure: {},
      statistics: {},
      quality: {},
    })!;
    expect(view.venue).toBe("Conference X");
    expect(view.journal).toBeUndefined();
  });

  it("maps scientific_structure framing without inventing fields", () => {
    const view = mapStructure({
      ...SAMPLE,
      scientific_structure: {
        schema_version: "1.0.0",
        section_skeleton: [
          { section_type: "methods", present: true, heading: "Methods", confidence: 0.9 },
        ],
        objectives: [
          {
            text: "The aim of this study was to evaluate widgets.",
            source: "abstract",
            confidence: 0.72,
          },
        ],
        research_questions: [],
        hypotheses: [],
        problem_statement: null,
      },
    })!;
    expect(view.scientificStructure?.objectives).toHaveLength(1);
    expect(view.scientificStructure?.objectives[0]?.text).toMatch(/aim/i);
    expect(view.scientificStructure?.sectionSkeleton[0]?.present).toBe(true);
    expect(view.scientificStructure?.hasFraming).toBe(true);
  });

  it("maps methodology_profile without inventing fields", () => {
    const view = mapStructure({
      ...SAMPLE,
      methodology_profile: {
        schema_version: "1.0.0",
        study_design: {
          text: "randomized controlled trial",
          label: "randomized_controlled_trial",
          kind: "study_design",
          source: "methods",
          confidence: 0.9,
        },
        population: null,
        sample_size: {
          text: "n = 120",
          label: "120",
          kind: "sample_size",
          source: "methods",
          confidence: 0.85,
        },
        intervention: null,
        controls: null,
        dataset: null,
        experimental_setup: null,
        variables: [],
        metrics: [{ text: "accuracy", kind: "metrics", source: "methods", confidence: 0.7 }],
        code_available: null,
        dataset_available: null,
        has_content: true,
        methods_section_present: true,
      },
    })!;
    expect(view.methodologyProfile?.hasContent).toBe(true);
    expect(view.methodologyProfile?.studyDesign?.label).toBe("randomized_controlled_trial");
    expect(view.methodologyProfile?.sampleSize?.text).toMatch(/120/);
    expect(view.methodologyProfile?.metrics).toHaveLength(1);
    expect(view.methodologyProfile?.population).toBeNull();
  });

  it("treats empty methodology_profile as no content", () => {
    const view = mapStructure({
      ...SAMPLE,
      methodology_profile: {
        schema_version: "1.0.0",
        study_design: null,
        population: null,
        sample_size: null,
        intervention: null,
        controls: null,
        dataset: null,
        experimental_setup: null,
        variables: [],
        metrics: [],
        code_available: null,
        dataset_available: null,
        has_content: false,
        methods_section_present: false,
      },
    })!;
    expect(view.methodologyProfile?.hasContent).toBe(false);
  });

  it("maps statistics_profile and keeps only author_stated interpretations", () => {
    const view = mapStructure({
      ...SAMPLE,
      statistics_profile: {
        schema_version: "1.0.0",
        tests: [
          {
            text: "ANOVA",
            label: "anova",
            kind: "statistical_test",
            source: "results",
            confidence: 0.88,
          },
        ],
        p_values: [{ text: "p < 0.01", kind: "p_value", source: "results", confidence: 0.85 }],
        confidence_intervals: [],
        effect_sizes: [{ text: "HR = 1.45", kind: "effect_size", source: "results", confidence: 0.85 }],
        other_measures: [],
        interpretations: [
          {
            text: "The effect was statistically significant.",
            kind: "interpretation",
            source: "results",
            confidence: 0.78,
            author_stated: true,
          },
          {
            text: "Should be dropped — invented significance",
            kind: "interpretation",
            source: "results",
            confidence: 0.5,
            author_stated: false,
          },
        ],
        has_content: true,
        results_section_present: true,
      },
    })!;
    expect(view.statisticsProfile?.hasContent).toBe(true);
    expect(view.statisticsProfile?.tests[0]?.label).toBe("anova");
    expect(view.statisticsProfile?.pValues).toHaveLength(1);
    expect(view.statisticsProfile?.effectSizes).toHaveLength(1);
    expect(view.statisticsProfile?.interpretations).toHaveLength(1);
    expect(view.statisticsProfile?.interpretations[0]?.authorStated).toBe(true);
  });

  it("treats empty statistics_profile as no content", () => {
    const view = mapStructure({
      ...SAMPLE,
      statistics_profile: {
        schema_version: "1.0.0",
        tests: [],
        p_values: [],
        confidence_intervals: [],
        effect_sizes: [],
        other_measures: [],
        interpretations: [],
        has_content: false,
        results_section_present: false,
      },
    })!;
    expect(view.statisticsProfile?.hasContent).toBe(false);
  });

  it("maps limitations_novelty_profile author-stated items only", () => {
    const view = mapStructure({
      ...SAMPLE,
      limitations_novelty_profile: {
        schema_version: "1.0.0",
        limitations: [
          {
            text: "Single-center enrollment limits generalizability.",
            kind: "limitation",
            source: "discussion",
            confidence: 0.78,
            author_stated: true,
          },
          {
            text: "Invented critique should drop",
            kind: "limitation",
            source: "ai",
            author_stated: false,
          },
        ],
        novelty: [
          {
            text: "To our knowledge, we present a novel framework.",
            kind: "novelty",
            source: "abstract",
            confidence: 0.78,
            author_stated: true,
          },
        ],
        future_work: [],
        research_gaps: [],
        has_content: true,
        limitations_section_present: false,
      },
    })!;
    expect(view.limitationsNoveltyProfile?.hasContent).toBe(true);
    expect(view.limitationsNoveltyProfile?.limitations).toHaveLength(1);
    expect(view.limitationsNoveltyProfile?.novelty).toHaveLength(1);
    expect(view.limitationsNoveltyProfile?.limitations[0]?.authorStated).toBe(true);
  });

  it("treats empty limitations_novelty_profile as no content", () => {
    const view = mapStructure({
      ...SAMPLE,
      limitations_novelty_profile: {
        schema_version: "1.0.0",
        limitations: [],
        novelty: [],
        future_work: [],
        research_gaps: [],
        has_content: false,
        limitations_section_present: false,
      },
    })!;
    expect(view.limitationsNoveltyProfile?.hasContent).toBe(false);
  });

  it("maps quality_assessment_profile as inspectable checklist without numeric score", () => {
    const view = mapStructure({
      ...SAMPLE,
      quality_assessment_profile: {
        schema_version: "1.0.0",
        scoring: "inspectable_checklist",
        has_content: true,
        sections: [
          {
            id: "methodology",
            label: "Methodology",
            band: "strong",
            items: [
              {
                status: "pass",
                text: "randomized controlled trial",
                reason: "Study design extracted",
                source: "methodology_profile",
              },
            ],
          },
          {
            id: "evidence",
            label: "Evidence",
            band: "partial",
            items: [
              {
                status: "pass",
                text: "Statistical analysis reported",
                reason: "tests present",
              },
            ],
          },
        ],
      },
    })!;
    expect(view.qualityAssessment?.hasContent).toBe(true);
    expect(view.qualityAssessment?.scoring).toBe("inspectable_checklist");
    expect(view.qualityAssessment?.sections[0]?.band).toBe("strong");
    expect(view.qualityAssessment?.sections[0]?.items[0]?.reason).toMatch(/Study design/i);
    expect((view.qualityAssessment as { overall_score?: number } | null)?.overall_score).toBeUndefined();
  });
});

describe("formatQualityScore", () => {
  it("formats 0–1 scores as percent", () => {
    expect(formatQualityScore(0.85)).toBe("85%");
  });
});
