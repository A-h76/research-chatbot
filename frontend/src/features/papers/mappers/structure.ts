/**
 * Structure tab mapper — Phase 1 `document_understanding`.
 * Pattern: mapStructure(phase) → DocumentUnderstandingView → PaperStructureTab
 */

import type { PhaseResult } from "@/features/pipeline";

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
  sections: DocumentSectionRow[];
  warnings: string[];
  errors: string[];
  quality: DocumentQualityScores;
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
  const referenceCount = asNumber(statistics.reference_count);

  const sections = buildSections(structure);
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
      warnings.length ||
      errors.length ||
      hasQuality,
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
    warnings,
    errors,
    quality,
    hasContent,
  };
}

export function formatQualityScore(n: number | undefined): string | undefined {
  if (n == null) return undefined;
  // Backend stores 0–1 floats; show as percent without inventing precision claims
  if (n >= 0 && n <= 1) return `${Math.round(n * 100)}%`;
  return String(n);
}

/** @deprecated Prefer mapStructure — kept for transitional imports. */
export const parseDocumentUnderstanding = mapStructure;
