/**
 * Domain-neutral entities mapper.
 * Pattern: mapEntities(phase) → EntitiesViewModel → PaperEntitiesTab
 *
 * Today: adapts `medical_understanding`. Future disciplines can return the same view model.
 */

import type { PhaseResult } from "@/features/pipeline";
import {
  asBoolean,
  asNumber,
  asString,
  asStringArray,
  formatConfidence as formatEntityConfidenceShared,
  formatLabel,
  isRecord,
  normalizeEvidence,
  type EvidenceRefView,
} from "./shared";

export type EntityEvidenceView = EvidenceRefView;
export { normalizeEvidence };

export function formatEntityLabel(raw: string): string {
  return formatLabel(raw);
}

export function formatEntityConfidence(n: number | undefined): string | undefined {
  return formatEntityConfidenceShared(n);
}

/** Fixed ClinicalEntityType values from medical_understanding/enums.py */
export const CLINICAL_ENTITY_TYPES = [
  "condition",
  "drug",
  "procedure",
  "symptom",
  "lab_test",
  "anatomical_site",
  "device",
  "adverse_event",
  "biomarker",
  "other",
] as const;

export type ClinicalEntityType = (typeof CLINICAL_ENTITY_TYPES)[number];

const CLINICAL_TYPE_SET = new Set<string>(CLINICAL_ENTITY_TYPES);

export type EntityItemView = {
  /** Render key only — not a durable identity across re-analyses. */
  key: string;
  displayName: string;
  category: string;
  confidence?: number;
  synonyms: string[];
  evidence: EntityEvidenceView[];
  extras: Record<string, string | number | boolean>;
};

export type ClinicalEntityGroupView = {
  entityType: string;
  displayType: string;
  items: EntityItemView[];
};

export type PicoGroupView = {
  populations: EntityItemView[];
  interventions: EntityItemView[];
  comparators: EntityItemView[];
  outcomes: EntityItemView[];
};

export type EntitiesSummaryView = {
  overallConfidence?: number;
  clinicalEntityCount: number;
  interventionCount: number;
  populationCount: number;
  outcomeCount: number;
};

export type EntitiesViewModel = {
  skipped: boolean;
  skipReason?: string;
  overallConfidence?: number;
  warnings: string[];
  errors: string[];
  summary: EntitiesSummaryView;
  groups: {
    clinicalEntities: ClinicalEntityGroupView[];
    pico: PicoGroupView;
    statistics: EntityItemView[];
    findings: EntityItemView[];
    studyCharacteristics: EntityItemView[];
    temporal: EntityItemView[];
  };
  /**
   * True when the phase payload is usable for Ready UI
   * (including skipped docs and zero-entity extractions).
   */
  hasContent: boolean;
};

function makeKey(
  collection: string,
  entityType: string,
  value: string,
  index: number,
): string {
  return `${collection}:${entityType}:${value}:${index}`;
}

function extrasFrom(
  entries: Array<[string, string | number | boolean | undefined | null]>,
): Record<string, string | number | boolean> {
  const out: Record<string, string | number | boolean> = {};
  for (const [k, v] of entries) {
    if (v === undefined || v === null || v === "") continue;
    out[k] = v;
  }
  return out;
}

function mapClinicalEntities(raw: unknown): ClinicalEntityGroupView[] {
  if (!Array.isArray(raw)) return [];

  const buckets = new Map<string, EntityItemView[]>();
  for (const type of CLINICAL_ENTITY_TYPES) buckets.set(type, []);

  raw.forEach((item, index) => {
    if (!isRecord(item)) return;
    const value = asString(item.value);
    if (!value) return;
    const typeRaw = asString(item.entity_type) ?? "other";
    const entityType = CLINICAL_TYPE_SET.has(typeRaw) ? typeRaw : "other";
    const list = buckets.get(entityType) ?? buckets.get("other")!;
    list.push({
      key: makeKey("clinical_entities", entityType, value, index),
      displayName: value,
      category: entityType,
      confidence: asNumber(item.confidence),
      synonyms: asStringArray(item.synonyms),
      evidence: normalizeEvidence(item.evidence),
      extras: extrasFrom([
        ["rawText", asString(item.raw_text)],
        ["normalization", asString(item.normalization_status)],
      ]),
    });
  });

  return CLINICAL_ENTITY_TYPES.map((entityType) => ({
    entityType,
    displayType: formatEntityLabel(entityType),
    items: buckets.get(entityType) ?? [],
  })).filter((g) => g.items.length > 0);
}

function mapPopulations(raw: unknown): EntityItemView[] {
  if (!Array.isArray(raw)) return [];
  const out: EntityItemView[] = [];
  raw.forEach((item, index) => {
    if (!isRecord(item)) return;
    const description = asString(item.description);
    const sampleSize = asNumber(item.sample_size);
    const ageRange = asString(item.age_range);
    const inclusion = asStringArray(item.inclusion_criteria);
    const exclusion = asStringArray(item.exclusion_criteria);
    const confidence = asNumber(item.confidence);
    const evidence = normalizeEvidence(item.evidence);
    const displayName =
      description ||
      (sampleSize != null ? `n = ${sampleSize}` : undefined) ||
      ageRange ||
      (inclusion[0] ? `Inclusion: ${inclusion[0]}` : undefined);
    // Keep empty shells out of the UI; they are not useful concepts
    if (!displayName && evidence.length === 0 && (confidence == null || confidence === 0)) {
      return;
    }
    out.push({
      key: makeKey("populations", "population", displayName ?? `population-${index}`, index),
      displayName: displayName ?? "Population",
      category: "population",
      confidence,
      synonyms: [],
      evidence,
      extras: extrasFrom([
        ["sampleSize", sampleSize],
        ["ageRange", ageRange],
        ["inclusion", inclusion.length ? inclusion.join("; ") : undefined],
        ["exclusion", exclusion.length ? exclusion.join("; ") : undefined],
      ]),
    });
  });
  return out;
}

function mapInterventions(raw: unknown): EntityItemView[] {
  if (!Array.isArray(raw)) return [];
  const out: EntityItemView[] = [];
  raw.forEach((item, index) => {
    if (!isRecord(item)) return;
    const name = asString(item.name);
    if (!name) return;
    const interventionType = asString(item.intervention_type) ?? "other";
    out.push({
      key: makeKey("interventions", interventionType, name, index),
      displayName: name,
      category: interventionType,
      confidence: asNumber(item.confidence),
      synonyms: [],
      evidence: normalizeEvidence(item.evidence),
      extras: extrasFrom([
        ["dosage", asString(item.dosage)],
        ["route", asString(item.route)],
        ["duration", asString(item.duration)],
      ]),
    });
  });
  return out;
}

function mapComparators(raw: unknown): EntityItemView[] {
  if (!Array.isArray(raw)) return [];
  const out: EntityItemView[] = [];
  raw.forEach((item, index) => {
    if (!isRecord(item)) return;
    const name = asString(item.name);
    if (!name) return;
    out.push({
      key: makeKey("comparators", "comparator", name, index),
      displayName: name,
      category: "comparator",
      confidence: asNumber(item.confidence),
      synonyms: [],
      evidence: normalizeEvidence(item.evidence),
      extras: extrasFrom([
        ["isPlacebo", asBoolean(item.is_placebo)],
        ["isActiveControl", asBoolean(item.is_active_control)],
      ]),
    });
  });
  return out;
}

function mapOutcomes(raw: unknown): EntityItemView[] {
  if (!Array.isArray(raw)) return [];
  const out: EntityItemView[] = [];
  raw.forEach((item, index) => {
    if (!isRecord(item)) return;
    const name = asString(item.name);
    if (!name) return;
    const outcomeType = asString(item.outcome_type) ?? "other";
    out.push({
      key: makeKey("outcomes", outcomeType, name, index),
      displayName: name,
      category: outcomeType,
      confidence: asNumber(item.confidence),
      synonyms: [],
      evidence: normalizeEvidence(item.evidence),
      extras: extrasFrom([
        ["measurementMethod", asString(item.measurement_method)],
        ["timePoint", asString(item.time_point)],
      ]),
    });
  });
  return out;
}

function mapStatistics(raw: unknown): EntityItemView[] {
  if (!Array.isArray(raw)) return [];
  const out: EntityItemView[] = [];
  raw.forEach((item, index) => {
    if (!isRecord(item)) return;
    const measureType = asString(item.measure_type) ?? "statistic";
    const value = asString(item.value);
    if (!value) return;
    out.push({
      key: makeKey("statistical_measures", measureType, value, index),
      displayName: value,
      category: measureType,
      confidence: asNumber(item.confidence),
      synonyms: [],
      evidence: normalizeEvidence(item.evidence),
      extras: extrasFrom([["associatedOutcome", asString(item.associated_outcome)]]),
    });
  });
  return out;
}

function mapFindings(raw: unknown): EntityItemView[] {
  if (!Array.isArray(raw)) return [];
  const out: EntityItemView[] = [];
  raw.forEach((item, index) => {
    if (!isRecord(item)) return;
    const statement = asString(item.statement);
    if (!statement) return;
    out.push({
      key: makeKey("key_findings", "finding", statement.slice(0, 48), index),
      displayName: statement,
      category: "finding",
      confidence: asNumber(item.confidence),
      synonyms: [],
      evidence: normalizeEvidence(item.evidence),
      extras: extrasFrom([["supportingOutcome", asString(item.supporting_outcome)]]),
    });
  });
  return out;
}

function mapStudyCharacteristics(raw: unknown): EntityItemView[] {
  if (!isRecord(raw)) return [];
  const studyDesign = asString(raw.study_design);
  const blinding = asString(raw.blinding);
  const randomization = asString(raw.randomization_method);
  const arms = asNumber(raw.number_of_arms);
  const sites = asNumber(raw.number_of_sites);
  const multicenter = asBoolean(raw.multicenter);
  const confidence = asNumber(raw.confidence);
  const evidence = normalizeEvidence(raw.evidence);

  const hasAny =
    studyDesign ||
    blinding ||
    randomization ||
    arms != null ||
    sites != null ||
    multicenter != null ||
    evidence.length > 0;
  if (!hasAny) return [];

  return [
    {
      key: makeKey("study_characteristics", "study", studyDesign ?? "study", 0),
      displayName: studyDesign ? formatEntityLabel(studyDesign) : "Study characteristics",
      category: "study",
      confidence,
      synonyms: [],
      evidence,
      extras: extrasFrom([
        ["blinding", blinding],
        ["randomization", randomization],
        ["arms", arms],
        ["sites", sites],
        ["multicenter", multicenter],
      ]),
    },
  ];
}

function mapTemporal(raw: unknown): EntityItemView[] {
  if (!isRecord(raw)) return [];
  const duration = asString(raw.study_duration);
  const followUp = asString(raw.follow_up_period);
  const enrollment = asString(raw.enrollment_period);
  const timepoints = asStringArray(raw.key_timepoints);
  const confidence = asNumber(raw.confidence);
  const evidence = normalizeEvidence(raw.evidence);

  const parts = [duration, followUp, enrollment].filter(Boolean) as string[];
  if (!parts.length && !timepoints.length && !evidence.length) return [];

  return [
    {
      key: makeKey("temporal_data", "temporal", parts[0] ?? "temporal", 0),
      displayName: parts[0] ?? "Temporal data",
      category: "temporal",
      confidence,
      synonyms: [],
      evidence,
      extras: extrasFrom([
        ["studyDuration", duration],
        ["followUp", followUp],
        ["enrollment", enrollment],
        ["timepoints", timepoints.length ? timepoints.join("; ") : undefined],
      ]),
    },
  ];
}

function countFromSummary(summary: Record<string, unknown>, key: string, fallback: number): number {
  const counts = isRecord(summary.entity_counts) ? summary.entity_counts : {};
  return asNumber(counts[key]) ?? fallback;
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
    const extractor = asString(item.extractor);
    if (msg && extractor) out.push(`${extractor}: ${msg}`);
    else if (msg) out.push(msg);
  }
  return out;
}

/**
 * Adapt opaque medical_understanding (or future discipline) phase JSON
 * into a stable, domain-neutral EntitiesViewModel.
 */
export function mapEntities(phase: PhaseResult | null | undefined): EntitiesViewModel | null {
  if (!phase || !isRecord(phase)) return null;

  const skipped = phase.skipped === true;
  const skipReason = asString(phase.reasoning);
  const warnings = asStringArray(phase.warnings);
  const errors = errorMessages(phase.errors);

  const confidenceObj = isRecord(phase.confidence) ? phase.confidence : {};
  const overallConfidence = asNumber(confidenceObj.overall);

  const clinicalEntities = mapClinicalEntities(phase.clinical_entities);
  // Canonical PICO: top-level arrays only — do not mirror pico_elements
  const pico: PicoGroupView = {
    populations: mapPopulations(phase.populations),
    interventions: mapInterventions(phase.interventions),
    comparators: mapComparators(phase.comparators),
    outcomes: mapOutcomes(phase.outcomes),
  };
  const statistics = mapStatistics(phase.statistical_measures);
  const findings = mapFindings(phase.key_findings);
  const studyCharacteristics = mapStudyCharacteristics(phase.study_characteristics);
  const temporal = mapTemporal(phase.temporal_data);

  const summaryRaw = isRecord(phase.extraction_summary) ? phase.extraction_summary : {};
  const clinicalEntityCount = countFromSummary(
    summaryRaw,
    "clinical_entities",
    clinicalEntities.reduce((n, g) => n + g.items.length, 0),
  );
  const interventionCount = countFromSummary(
    summaryRaw,
    "interventions",
    pico.interventions.length,
  );
  const populationCount = countFromSummary(summaryRaw, "populations", pico.populations.length);
  const outcomeCount = countFromSummary(summaryRaw, "outcomes", pico.outcomes.length);

  const hasGroupContent = Boolean(
    clinicalEntities.length ||
      pico.populations.length ||
      pico.interventions.length ||
      pico.comparators.length ||
      pico.outcomes.length ||
      statistics.length ||
      findings.length ||
      studyCharacteristics.length ||
      temporal.length ||
      warnings.length ||
      errors.length ||
      overallConfidence != null ||
      asString(phase.pipeline_version),
  );

  // Skipped phase is still a successful Ready result
  const hasContent = skipped || hasGroupContent || phase.skipped === false;

  return {
    skipped,
    skipReason,
    overallConfidence,
    warnings,
    errors,
    summary: {
      overallConfidence,
      clinicalEntityCount,
      interventionCount,
      populationCount,
      outcomeCount,
    },
    groups: {
      clinicalEntities,
      pico,
      statistics,
      findings,
      studyCharacteristics,
      temporal,
    },
    hasContent,
  };
}

/** Client-side search over displayName + synonyms (case-insensitive). */
export function filterEntityItems(items: EntityItemView[], query: string): EntityItemView[] {
  const q = query.trim().toLowerCase();
  if (!q) return items;
  return items.filter((item) => {
    if (item.displayName.toLowerCase().includes(q)) return true;
    return item.synonyms.some((s) => s.toLowerCase().includes(q));
  });
}

export function filterClinicalGroups(
  groups: ClinicalEntityGroupView[],
  query: string,
): ClinicalEntityGroupView[] {
  const q = query.trim().toLowerCase();
  if (!q) return groups;
  return groups
    .map((g) => ({ ...g, items: filterEntityItems(g.items, q) }))
    .filter((g) => g.items.length > 0);
}

export function filterPico(pico: PicoGroupView, query: string): PicoGroupView {
  return {
    populations: filterEntityItems(pico.populations, query),
    interventions: filterEntityItems(pico.interventions, query),
    comparators: filterEntityItems(pico.comparators, query),
    outcomes: filterEntityItems(pico.outcomes, query),
  };
}
