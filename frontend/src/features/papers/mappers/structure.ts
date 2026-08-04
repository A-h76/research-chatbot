/**
 * Structure tab mapper — Phase 1 `document_understanding`.
 * Pattern: mapStructure(phase) → DocumentUnderstandingView → PaperStructureTab
 */

import type { PhaseResult } from "@/features/pipeline";
import {
  looksLikeBibliographyHeading,
  parseCitationPreview,
  splitReferenceLines,
  type CitationPreview,
} from "./citationPreview";

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function asString(v: unknown): string | undefined {
  return typeof v === "string" && v.trim() ? v : undefined;
}

function asNumber(v: unknown): number | undefined {
  return typeof v === "number" && Number.isFinite(v) ? v : undefined;
}

function asStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string" && x.trim().length > 0);
}

function asStringMap(v: unknown): Record<string, string> {
  if (!isRecord(v)) return {};
  const out: Record<string, string> = {};
  for (const [k, val] of Object.entries(v)) {
    if (typeof val === "string") out[k] = val;
  }
  return out;
}

export type DocumentSectionRow = {
  heading: string;
  sectionType?: string;
  content?: string;
  contentChars?: number;
};

export type DocumentQualityScores = {
  ocr_quality?: number;
  extraction_quality?: number;
  metadata_quality?: number;
  section_quality?: number;
  layout_quality?: number;
  completeness?: number;
  confidence?: number;
};

export type ScientificStructureItem = {
  text: string;
  source?: string;
  confidence?: number;
  locator?: Record<string, string>;
  kind?: string;
};

export type SectionSkeletonRow = {
  sectionType: string;
  present: boolean;
  heading?: string;
  confidence?: number;
};

export type ScientificStructureView = {
  schemaVersion?: string;
  sectionSkeleton: SectionSkeletonRow[];
  objectives: ScientificStructureItem[];
  researchQuestions: ScientificStructureItem[];
  hypotheses: ScientificStructureItem[];
  problemStatement: ScientificStructureItem | null;
  hasFraming: boolean;
};

/** Paper Analysis 2.2 — consistent methods fields when reliably extractable. */
export type MethodologyField = {
  text: string;
  label?: string;
  kind?: string;
  source?: string;
  confidence?: number;
};

export type MethodologyProfileView = {
  schemaVersion?: string;
  studyDesign: MethodologyField | null;
  population: MethodologyField | null;
  sampleSize: MethodologyField | null;
  intervention: MethodologyField | null;
  controls: MethodologyField | null;
  dataset: MethodologyField | null;
  experimentalSetup: MethodologyField | null;
  variables: MethodologyField[];
  metrics: MethodologyField[];
  codeAvailable: MethodologyField | null;
  datasetAvailable: MethodologyField | null;
  methodsSectionPresent: boolean;
  hasContent: boolean;
};

/** Paper Analysis 2.3 — explicit statistical findings only. */
export type StatisticsFinding = {
  text: string;
  label?: string;
  kind?: string;
  source?: string;
  confidence?: number;
  authorStated?: boolean;
};

export type StatisticsProfileView = {
  schemaVersion?: string;
  tests: StatisticsFinding[];
  pValues: StatisticsFinding[];
  confidenceIntervals: StatisticsFinding[];
  effectSizes: StatisticsFinding[];
  otherMeasures: StatisticsFinding[];
  interpretations: StatisticsFinding[];
  resultsSectionPresent: boolean;
  hasContent: boolean;
};

/** Paper Analysis 2.5 — author-stated limitations / novelty only. */
export type LimitationsNoveltyItem = {
  text: string;
  label?: string;
  kind?: string;
  source?: string;
  confidence?: number;
  authorStated?: boolean;
};

export type LimitationsNoveltyProfileView = {
  schemaVersion?: string;
  limitations: LimitationsNoveltyItem[];
  novelty: LimitationsNoveltyItem[];
  futureWork: LimitationsNoveltyItem[];
  researchGaps: LimitationsNoveltyItem[];
  limitationsSectionPresent: boolean;
  hasContent: boolean;
};

/** Paper Analysis 2.7 — explainable quality checklist. */
export type QualityAssessmentItem = {
  status: "pass" | "note" | "missing";
  text: string;
  source?: string;
  reason?: string;
};

export type QualityAssessmentSection = {
  id: string;
  label: string;
  band: "strong" | "partial" | "weak" | "unknown";
  items: QualityAssessmentItem[];
};

export type QualityAssessmentView = {
  schemaVersion?: string;
  scoring: string;
  sections: QualityAssessmentSection[];
  hasContent: boolean;
};

export type DocumentUnderstandingView = {
  title?: string;
  subtitle?: string;
  authors: string[];
  journal?: string;
  venue?: string;
  publicationYear?: number;
  language?: string;
  doi?: string;
  abstract?: string;
  wordCount?: number;
  pageCount?: number;
  charCount?: number;
  headingCount?: number;
  sectionCount?: number;
  referenceCount?: number;
  /** Outline sections only — bibliography entries are in `references`. */
  sections: DocumentSectionRow[];
  /** Bibliography as a collection, not Structure headings. */
  references: CitationPreview[];
  warnings: string[];
  errors: string[];
  quality: DocumentQualityScores;
  /** Paper Analysis 2.1 — framing fields when reliably extractable. */
  scientificStructure: ScientificStructureView | null;
  /** Paper Analysis 2.2 — methodology profile when reliably extractable. */
  methodologyProfile: MethodologyProfileView | null;
  /** Paper Analysis 2.3 — statistical findings when explicitly reported. */
  statisticsProfile: StatisticsProfileView | null;
  /** Paper Analysis 2.5 — author-stated limitations / novelty. */
  limitationsNoveltyProfile: LimitationsNoveltyProfileView | null;
  /** Paper Analysis 2.7 — inspectable checklist (not opaque scores). */
  qualityAssessment: QualityAssessmentView | null;
  /** True when at least one displayable field exists. */
  hasContent: boolean;
};

function buildSections(structure: Record<string, unknown>): DocumentSectionRow[] {
  const order = asStringArray(structure.heading_order);
  const rawHeadings = asStringMap(structure.raw_headings);
  const sectionTypes = isRecord(structure.section_types)
    ? (structure.section_types as Record<string, unknown>)
    : {};

  const headings = order.length > 0 ? order : Object.keys(rawHeadings);
  return headings.map((heading) => {
    const content = asString(rawHeadings[heading]);
    const typeRaw = sectionTypes[heading];
    const sectionType = typeof typeRaw === "string" ? typeRaw : undefined;
    return {
      heading,
      sectionType,
      content,
      contentChars: content?.length,
    };
  });
}

function sectionToCitationRaw(s: DocumentSectionRow): string {
  const body = s.content?.trim();
  // Prefer the heading when the citation text lives there (common DU false-positive).
  if (looksLikeBibliographyHeading(s.heading, s.content, s.sectionType)) {
    if (!body || body.length < 12) return s.heading;
    // Avoid duplicating if content already starts with the same number
    if (body.startsWith(s.heading.slice(0, 12))) return body;
    return `${s.heading} ${body}`;
  }
  return body || s.heading;
}

function collectReferences(
  structure: Record<string, unknown>,
  sections: DocumentSectionRow[],
): CitationPreview[] {
  const fromApi = asStringArray(structure.references).map((raw, i) =>
    parseCitationPreview(raw, i),
  );

  const refSection = sections.find(
    (s) =>
      (s.sectionType ?? "").toLowerCase() === "references" ||
      /^references?$/i.test(s.heading.trim()),
  );
  const fromSectionBody =
    refSection?.content && splitReferenceLines(refSection.content).length > 0
      ? splitReferenceLines(refSection.content).map((raw, i) => parseCitationPreview(raw, i))
      : [];

  // Numbered citation lines wrongly promoted to Structure headings (often 50–200 rows).
  const stolen = sections.filter((s) =>
    looksLikeBibliographyHeading(s.heading, s.content, s.sectionType),
  );
  const fromStolen =
    stolen.length >= 3
      ? stolen.map((s, i) => parseCitationPreview(sectionToCitationRaw(s), i))
      : [];

  // Prefer the richest source so a thin structure.references list (e.g. 7)
  // does not leave 90+ false outline rows behind.
  const sources = [fromStolen, fromSectionBody, fromApi].sort(
    (a, b) => b.length - a.length,
  );
  return sources[0] ?? [];
}

function filterOutlineSections(sections: DocumentSectionRow[]): DocumentSectionRow[] {
  // Always strip bibliography noise from the outline — References belong in ReferenceBrowser.
  return sections.filter((s) => {
    if ((s.sectionType ?? "").toLowerCase() === "references") return false;
    if (/^references?$/i.test(s.heading.trim())) return false;
    if (looksLikeBibliographyHeading(s.heading, s.content, s.sectionType)) return false;
    return true;
  });
}

function mapScientificItem(v: unknown): ScientificStructureItem | null {
  if (!isRecord(v)) return null;
  const text = asString(v.text);
  if (!text) return null;
  const locatorRaw = isRecord(v.locator) ? v.locator : undefined;
  const locator: Record<string, string> | undefined = locatorRaw
    ? Object.fromEntries(
        Object.entries(locatorRaw).filter(([, val]) => typeof val === "string") as [
          string,
          string,
        ][],
      )
    : undefined;
  return {
    text,
    source: asString(v.source),
    confidence: asNumber(v.confidence),
    locator,
    kind: asString(v.kind),
  };
}

function mapScientificStructure(raw: unknown): ScientificStructureView | null {
  if (!isRecord(raw)) return null;
  const objectives = (Array.isArray(raw.objectives) ? raw.objectives : [])
    .map(mapScientificItem)
    .filter((x): x is ScientificStructureItem => x != null);
  const researchQuestions = (Array.isArray(raw.research_questions) ? raw.research_questions : [])
    .map(mapScientificItem)
    .filter((x): x is ScientificStructureItem => x != null);
  const hypotheses = (Array.isArray(raw.hypotheses) ? raw.hypotheses : [])
    .map(mapScientificItem)
    .filter((x): x is ScientificStructureItem => x != null);
  const problemStatement = mapScientificItem(raw.problem_statement);
  const sectionSkeleton: SectionSkeletonRow[] = (
    Array.isArray(raw.section_skeleton) ? raw.section_skeleton : []
  )
    .map((row): SectionSkeletonRow | null => {
      if (!isRecord(row)) return null;
      const sectionType = asString(row.section_type);
      if (!sectionType) return null;
      const heading = asString(row.heading);
      const confidence = asNumber(row.confidence);
      const out: SectionSkeletonRow = {
        sectionType,
        present: Boolean(row.present),
      };
      if (heading) out.heading = heading;
      if (confidence != null) out.confidence = confidence;
      return out;
    })
    .filter((x): x is SectionSkeletonRow => x != null);

  const hasFraming = Boolean(
    objectives.length ||
      researchQuestions.length ||
      hypotheses.length ||
      problemStatement ||
      sectionSkeleton.some((s) => s.present),
  );

  return {
    schemaVersion: asString(raw.schema_version),
    sectionSkeleton,
    objectives,
    researchQuestions,
    hypotheses,
    problemStatement,
    hasFraming,
  };
}

function mapMethodologyField(v: unknown): MethodologyField | null {
  if (!isRecord(v)) return null;
  const text = asString(v.text);
  if (!text) return null;
  return {
    text,
    label: asString(v.label),
    kind: asString(v.kind),
    source: asString(v.source),
    confidence: asNumber(v.confidence),
  };
}

function mapMethodologyFieldList(raw: unknown): MethodologyField[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map(mapMethodologyField)
    .filter((x): x is MethodologyField => x != null);
}

function mapMethodologyProfile(raw: unknown): MethodologyProfileView | null {
  if (!isRecord(raw)) return null;
  const studyDesign = mapMethodologyField(raw.study_design);
  const population = mapMethodologyField(raw.population);
  const sampleSize = mapMethodologyField(raw.sample_size);
  const intervention = mapMethodologyField(raw.intervention);
  const controls = mapMethodologyField(raw.controls);
  const dataset = mapMethodologyField(raw.dataset);
  const experimentalSetup = mapMethodologyField(raw.experimental_setup);
  const variables = mapMethodologyFieldList(raw.variables);
  const metrics = mapMethodologyFieldList(raw.metrics);
  const codeAvailable = mapMethodologyField(raw.code_available);
  const datasetAvailable = mapMethodologyField(raw.dataset_available);
  const hasContent = Boolean(
    studyDesign ||
      population ||
      sampleSize ||
      intervention ||
      controls ||
      dataset ||
      experimentalSetup ||
      variables.length ||
      metrics.length ||
      codeAvailable ||
      datasetAvailable,
  );
  return {
    schemaVersion: asString(raw.schema_version),
    studyDesign,
    population,
    sampleSize,
    intervention,
    controls,
    dataset,
    experimentalSetup,
    variables,
    metrics,
    codeAvailable,
    datasetAvailable,
    methodsSectionPresent: Boolean(raw.methods_section_present),
    hasContent,
  };
}

function mapStatisticsFinding(v: unknown): StatisticsFinding | null {
  if (!isRecord(v)) return null;
  const text = asString(v.text);
  if (!text) return null;
  return {
    text,
    label: asString(v.label),
    kind: asString(v.kind),
    source: asString(v.source),
    confidence: asNumber(v.confidence),
    authorStated: v.author_stated === true,
  };
}

function mapStatisticsFindingList(raw: unknown): StatisticsFinding[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map(mapStatisticsFinding)
    .filter((x): x is StatisticsFinding => x != null);
}

function mapStatisticsProfile(raw: unknown): StatisticsProfileView | null {
  if (!isRecord(raw)) return null;
  const tests = mapStatisticsFindingList(raw.tests);
  const pValues = mapStatisticsFindingList(raw.p_values);
  const confidenceIntervals = mapStatisticsFindingList(raw.confidence_intervals);
  const effectSizes = mapStatisticsFindingList(raw.effect_sizes);
  const otherMeasures = mapStatisticsFindingList(raw.other_measures);
  const interpretations = mapStatisticsFindingList(raw.interpretations).filter(
    (i) => i.authorStated === true,
  );
  const hasContent = Boolean(
    tests.length ||
      pValues.length ||
      confidenceIntervals.length ||
      effectSizes.length ||
      otherMeasures.length ||
      interpretations.length,
  );
  return {
    schemaVersion: asString(raw.schema_version),
    tests,
    pValues,
    confidenceIntervals,
    effectSizes,
    otherMeasures,
    interpretations,
    resultsSectionPresent: Boolean(raw.results_section_present),
    hasContent,
  };
}

function mapLimitationsNoveltyItem(v: unknown): LimitationsNoveltyItem | null {
  if (!isRecord(v)) return null;
  const text = asString(v.text);
  if (!text) return null;
  // Prefer author-stated; Narrative enrich is still paper-scoped author/LLM paraphrase of paper.
  if (v.author_stated === false) return null;
  return {
    text,
    label: asString(v.label),
    kind: asString(v.kind),
    source: asString(v.source),
    confidence: asNumber(v.confidence),
    authorStated: v.author_stated !== false,
  };
}

function mapLimitationsNoveltyList(raw: unknown): LimitationsNoveltyItem[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map(mapLimitationsNoveltyItem)
    .filter((x): x is LimitationsNoveltyItem => x != null);
}

function mapLimitationsNoveltyProfile(raw: unknown): LimitationsNoveltyProfileView | null {
  if (!isRecord(raw)) return null;
  const limitations = mapLimitationsNoveltyList(raw.limitations);
  const novelty = mapLimitationsNoveltyList(raw.novelty);
  const futureWork = mapLimitationsNoveltyList(raw.future_work);
  const researchGaps = mapLimitationsNoveltyList(raw.research_gaps);
  const hasContent = Boolean(
    limitations.length || novelty.length || futureWork.length || researchGaps.length,
  );
  return {
    schemaVersion: asString(raw.schema_version),
    limitations,
    novelty,
    futureWork,
    researchGaps,
    limitationsSectionPresent: Boolean(raw.limitations_section_present),
    hasContent,
  };
}

function mapQualityAssessmentItem(v: unknown): QualityAssessmentItem | null {
  if (!isRecord(v)) return null;
  const text = asString(v.text);
  if (!text) return null;
  const statusRaw = asString(v.status) || "note";
  const status =
    statusRaw === "pass" || statusRaw === "missing" || statusRaw === "note"
      ? statusRaw
      : "note";
  return {
    status,
    text,
    source: asString(v.source),
    reason: asString(v.reason),
  };
}

function mapQualityAssessment(raw: unknown): QualityAssessmentView | null {
  if (!isRecord(raw)) return null;
  const sections: QualityAssessmentSection[] = [];
  for (const sec of Array.isArray(raw.sections) ? raw.sections : []) {
    if (!isRecord(sec)) continue;
    const id = asString(sec.id);
    const label = asString(sec.label);
    if (!id || !label) continue;
    const bandRaw = (asString(sec.band) || "unknown").toLowerCase();
    const band =
      bandRaw === "strong" ||
      bandRaw === "partial" ||
      bandRaw === "weak" ||
      bandRaw === "unknown"
        ? bandRaw
        : "unknown";
    const items = (Array.isArray(sec.items) ? sec.items : [])
      .map(mapQualityAssessmentItem)
      .filter((x): x is QualityAssessmentItem => x != null);
    sections.push({ id, label, band, items });
  }
  const hasContent = Boolean(
    raw.has_content === true ||
      sections.some((s) => s.items.length > 0 || s.band !== "unknown"),
  );
  return {
    schemaVersion: asString(raw.schema_version),
    scoring: asString(raw.scoring) || "inspectable_checklist",
    sections,
    hasContent,
  };
}

/**
 * Parse opaque phase `result` into a Structure-tab view model.
 * Returns null if `result` is not a usable object.
 */
export function mapStructure(result: PhaseResult | null | undefined): DocumentUnderstandingView | null {
  if (!result || !isRecord(result)) return null;

  const metadata = isRecord(result.metadata) ? result.metadata : {};
  const structure = isRecord(result.structure) ? result.structure : {};
  const statistics = isRecord(result.statistics) ? result.statistics : {};
  const qualityRaw = isRecord(result.quality) ? result.quality : {};
  const scientificStructure = mapScientificStructure(result.scientific_structure);
  const methodologyProfile = mapMethodologyProfile(result.methodology_profile);
  const statisticsProfile = mapStatisticsProfile(result.statistics_profile);
  const limitationsNoveltyProfile = mapLimitationsNoveltyProfile(
    result.limitations_novelty_profile,
  );
  const qualityAssessment = mapQualityAssessment(result.quality_assessment_profile);

  const authors = asStringArray(metadata.authors);
  const title = asString(metadata.title);
  const subtitle = asString(metadata.subtitle);
  const journal = asString(metadata.journal);
  const venue = asString(metadata.venue);
  const publicationYear = asNumber(metadata.publication_year) ?? asNumber(metadata.year);
  const language = asString(metadata.language);
  const doi = asString(metadata.doi);
  const abstract = asString(metadata.abstract);

  const wordCount = asNumber(statistics.word_count);
  const pageCount = asNumber(statistics.page_count);
  const charCount = asNumber(statistics.char_count);
  const headingCount = asNumber(statistics.heading_count);
  const sectionCount = asNumber(statistics.section_count);

  const allSections = buildSections(structure);
  const references = collectReferences(structure, allSections);
  const sections = filterOutlineSections(allSections);
  const statsCount = asNumber(statistics.reference_count);
  const referenceCount = references.length > 0 ? references.length : statsCount;

  const warnings = asStringArray(qualityRaw.warnings);
  const errors = asStringArray(qualityRaw.errors);

  const quality: DocumentQualityScores = {
    ocr_quality: asNumber(qualityRaw.ocr_quality),
    extraction_quality: asNumber(qualityRaw.extraction_quality),
    metadata_quality: asNumber(qualityRaw.metadata_quality),
    section_quality: asNumber(qualityRaw.section_quality),
    layout_quality: asNumber(qualityRaw.layout_quality),
    completeness: asNumber(qualityRaw.completeness),
    confidence: asNumber(qualityRaw.confidence),
  };

  const hasQuality = Object.values(quality).some((v) => v !== undefined);
  const hasContent = Boolean(
    title ||
      subtitle ||
      authors.length ||
      journal ||
      venue ||
      publicationYear != null ||
      language ||
      doi ||
      abstract ||
      wordCount != null ||
      pageCount != null ||
      sections.length ||
      references.length ||
      warnings.length ||
      errors.length ||
      hasQuality ||
      scientificStructure?.hasFraming ||
      methodologyProfile?.hasContent ||
      statisticsProfile?.hasContent ||
      limitationsNoveltyProfile?.hasContent ||
      qualityAssessment?.hasContent,
  );

  return {
    title,
    subtitle,
    authors,
    journal,
    venue,
    publicationYear,
    language,
    doi,
    abstract,
    wordCount,
    pageCount,
    charCount,
    headingCount,
    sectionCount,
    referenceCount,
    sections,
    references,
    warnings,
    errors,
    quality,
    scientificStructure,
    methodologyProfile,
    statisticsProfile,
    limitationsNoveltyProfile,
    qualityAssessment,
    hasContent,
  };
}

export function formatQualityScore(n: number | undefined): string | undefined {
  if (n == null) return undefined;
  if (n >= 0 && n <= 1) return `${Math.round(n * 100)}%`;
  return String(n);
}

/** @deprecated Prefer mapStructure — kept for transitional imports. */
export const parseDocumentUnderstanding = mapStructure;
