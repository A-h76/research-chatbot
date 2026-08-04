import { describe, it, expect } from "vitest";
import {
  mapEntities,
  normalizeEvidence,
  filterEntityItems,
  filterClinicalGroups,
  enrichEntitiesWithScientificProfile,
} from "./mappers/entities";
import type { PhaseResult } from "@/features/pipeline";

const SAMPLE: PhaseResult = {
  skipped: false,
  reasoning: null,
  clinical_entities: [
    {
      value: "diabetes mellitus",
      entity_type: "condition",
      raw_text: "diabetes",
      normalization_status: "synonym_match",
      confidence: 0.7,
      evidence: {
        page: 1,
        section: "abstract",
        paragraph: 0,
        character_range: [139, 147],
        text_snippet: "Patients with diabetes",
        confidence: 0.7,
      },
      synonyms: ["dm", "diabetes"],
    },
    {
      value: "metformin",
      entity_type: "drug",
      raw_text: "metformin",
      normalization_status: "unknown",
      confidence: 0.7,
      evidence: {
        page: 1,
        section: "methods",
        text_snippet: "receive metformin",
        confidence: 0.7,
      },
      synonyms: [],
    },
  ],
  pico_elements: {
    population: { description: "", confidence: 0, evidence: null },
    interventions: [{ name: "should-not-appear-from-pico", confidence: 0.9 }],
    comparators: [],
    outcomes: [],
    confidence: 0.5,
  },
  interventions: [
    {
      name: "metformin",
      intervention_type: "drug",
      dosage: null,
      route: null,
      duration: null,
      confidence: 0.7,
      evidence: { page: 1, section: "methods", text_snippet: "metformin", confidence: 0.7 },
    },
  ],
  populations: [
    {
      description: "",
      sample_size: null,
      inclusion_criteria: [],
      exclusion_criteria: [],
      age_range: null,
      confidence: 0,
      evidence: null,
    },
  ],
  comparators: [
    {
      name: "placebo",
      is_placebo: true,
      is_active_control: false,
      confidence: 0.7,
      evidence: null,
    },
  ],
  outcomes: [
    {
      name: "Primary outcome at 12 weeks",
      outcome_type: "primary",
      confidence: 0.7,
      evidence: [],
    },
  ],
  statistical_measures: [
    {
      measure_type: "p_value",
      value: "p=0.002",
      associated_outcome: null,
      confidence: 0.75,
      evidence: { text_snippet: "p=0.002", confidence: 0.75 },
    },
  ],
  key_findings: [
    {
      statement: "Significant reduction in HbA1c",
      supporting_outcome: null,
      confidence: 0.7,
      evidence: null,
    },
  ],
  study_characteristics: {
    study_design: "rct",
    number_of_arms: 2,
    blinding: "double-blind",
    multicenter: true,
    confidence: 0.7,
    evidence: [],
  },
  temporal_data: {
    study_duration: "Study duration of 24 weeks",
    follow_up_period: "Follow-up period of 52 weeks",
    enrollment_period: null,
    key_timepoints: [],
    confidence: 0.7,
    evidence: [{ text_snippet: "24 weeks", confidence: 0.7 }],
  },
  demographic_data: null,
  extraction_summary: {
    entity_counts: {
      clinical_entities: 2,
      populations: 1,
      interventions: 1,
      comparators: 1,
      outcomes: 1,
      statistical_measures: 1,
      key_findings: 1,
    },
    total_entities: 7,
  },
  confidence: {
    overall: 0.69,
    components: { section_quality: 1 },
    formula: "…",
  },
  errors: [],
  warnings: [],
  recoveries: [],
  processing_time_ms: 12,
  pipeline_version: "1.0.0",
};

describe("normalizeEvidence", () => {
  it("normalizes object, null, and array to a list", () => {
    expect(normalizeEvidence(null)).toEqual([]);
    expect(normalizeEvidence({ text_snippet: "a", confidence: 0.5 })).toEqual([
      { textSnippet: "a", confidence: 0.5 },
    ]);
    expect(
      normalizeEvidence([
        { text_snippet: "a", page: 1 },
        { text_snippet: "b", section: "methods" },
      ]),
    ).toHaveLength(2);
  });
});

describe("mapEntities", () => {
  it("returns null for non-objects", () => {
    expect(mapEntities(null)).toBeNull();
    expect(mapEntities(undefined)).toBeNull();
  });

  it("groups clinical entities by entity_type and preserves cross-collection duplicates", () => {
    const view = mapEntities(SAMPLE)!;
    expect(view.skipped).toBe(false);
    expect(view.groups.clinicalEntities.map((g) => g.entityType)).toEqual([
      "condition",
      "drug",
    ]);
    expect(view.groups.clinicalEntities[0].items[0]).toMatchObject({
      displayName: "diabetes mellitus",
      synonyms: ["dm", "diabetes"],
      confidence: 0.7,
    });
    // metformin as drug entity AND intervention — both kept
    expect(view.groups.clinicalEntities[1].items[0].displayName).toBe("metformin");
    expect(view.groups.pico.interventions[0].displayName).toBe("metformin");
    expect(view.groups.pico.interventions[0].key).toContain("interventions:");
    expect(view.groups.clinicalEntities[1].items[0].key).toContain("clinical_entities:");
  });

  it("uses top-level PICO arrays, not pico_elements", () => {
    const view = mapEntities(SAMPLE)!;
    expect(view.groups.pico.interventions.map((i) => i.displayName)).toEqual(["metformin"]);
    expect(
      view.groups.pico.interventions.some((i) => i.displayName === "should-not-appear-from-pico"),
    ).toBe(false);
    // empty population shell omitted
    expect(view.groups.pico.populations).toEqual([]);
  });

  it("maps summary counts from extraction_summary", () => {
    const view = mapEntities(SAMPLE)!;
    expect(view.summary).toEqual({
      overallConfidence: 0.69,
      clinicalEntityCount: 2,
      interventionCount: 1,
      populationCount: 1,
      outcomeCount: 1,
      scientificEntityCount: 0,
    });
  });

  it("treats skipped documents as Ready content with reason", () => {
    const view = mapEntities({
      skipped: true,
      reasoning: "document not medical/clinical (routing: unknown)",
      clinical_entities: [],
      interventions: [],
      populations: [],
      comparators: [],
      outcomes: [],
      statistical_measures: [],
      key_findings: [],
      pico_elements: null,
      confidence: { overall: 0, components: {}, formula: "" },
      extraction_summary: { entity_counts: {} },
      warnings: ["sparse input"],
      errors: [],
      pipeline_version: "1.0.0",
    })!;
    expect(view.skipped).toBe(true);
    expect(view.skipReason).toMatch(/not medical/i);
    expect(view.hasContent).toBe(true);
    expect(view.warnings).toEqual(["sparse input"]);
    expect(view.groups.clinicalEntities).toEqual([]);
  });

  it("treats zero-entity non-skipped results as Ready content", () => {
    const view = mapEntities({
      skipped: false,
      clinical_entities: [],
      interventions: [],
      populations: [],
      comparators: [],
      outcomes: [],
      confidence: { overall: 0.1, components: {}, formula: "" },
      extraction_summary: { entity_counts: { clinical_entities: 0 } },
      warnings: [],
      errors: [],
      pipeline_version: "1.0.0",
    })!;
    expect(view.hasContent).toBe(true);
    expect(view.summary.clinicalEntityCount).toBe(0);
  });
});

describe("enrichEntitiesWithScientificProfile", () => {
  it("fills scientific entities when medical is skipped", () => {
    const medical = mapEntities({
      skipped: true,
      reasoning: "not medical",
      clinical_entities: [],
      interventions: [],
      populations: [],
      comparators: [],
      outcomes: [],
      warnings: [],
      errors: [],
    });
    const view = enrichEntitiesWithScientificProfile(medical, {
      has_content: true,
      entities: [
        {
          value: "ImageNet",
          entity_type: "dataset",
          confidence: 0.8,
          source: "methodology_profile",
        },
        {
          value: "accuracy",
          entity_type: "metric",
          confidence: 0.8,
          source: "methodology_profile",
        },
      ],
      relations: [
        {
          subject: "cohort",
          predicate: "uses",
          object: "ImageNet",
          confidence: 0.75,
        },
      ],
    })!;
    expect(view.skipped).toBe(true);
    expect(view.summary.scientificEntityCount).toBe(2);
    expect(view.groups.scientificEntities.length).toBeGreaterThan(0);
    expect(view.localRelations).toHaveLength(1);
    expect(view.hasContent).toBe(true);
  });
});

describe("filterEntityItems / filterClinicalGroups", () => {
  it("searches displayName and synonyms", () => {
    const view = mapEntities(SAMPLE)!;
    const condition = view.groups.clinicalEntities.find((g) => g.entityType === "condition")!;
    expect(filterEntityItems(condition.items, "dm")).toHaveLength(1);
    expect(filterEntityItems(condition.items, "hypertension")).toHaveLength(0);
    expect(filterClinicalGroups(view.groups.clinicalEntities, "metformin")).toEqual([
      expect.objectContaining({ entityType: "drug" }),
    ]);
  });
});
