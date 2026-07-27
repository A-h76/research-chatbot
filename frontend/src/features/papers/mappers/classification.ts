/**
 * Classification tab mapper — Phase 1.2 `classification` (+ analysis_context summary).
 * Pattern: mapClassification(phase) → ClassificationViewModel → PaperClassificationTab
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

/** Display titles for the four decision families (UI copy, not backend values). */
export const DECISION_FAMILIES = [
  { key: "document_type", title: "Document type" },
  { key: "domain", title: "Domain" },
  { key: "study_design", title: "Study design" },
  { key: "reporting_guideline", title: "Reporting guideline" },
] as const;

export type DecisionFamilyKey = (typeof DECISION_FAMILIES)[number]["key"];

/** Known short / acronym labels — formatting only, never invents a classification. */
const LABEL_DISPLAY: Record<string, string> = {
  rct: "RCT",
  ai_ml: "AI/ML",
  consort: "CONSORT",
  prisma: "PRISMA",
  strobe: "STROBE",
  care: "CARE",
  stard: "STARD",
  spirit: "SPIRIT",
  tripod: "TRIPOD",
  arrive: "ARRIVE",
  cheers: "CHEERS",
};

export function formatClassificationLabel(raw: string): string {
  const key = raw.trim().toLowerCase();
  if (LABEL_DISPLAY[key]) return LABEL_DISPLAY[key];
  return raw
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/**
 * Display backend 0–1 confidence consistently (DESIGN-SYSTEM: % for UI).
 * Does not invent scores — only formats the given float.
 */
export function formatConfidence(n: number | undefined): string | undefined {
  if (n == null) return undefined;
  if (n >= 0 && n <= 1) return `${Math.round(n * 100)}%`;
  return String(n);
}

export type ClassificationDecisionView = {
  family: DecisionFamilyKey;
  familyTitle: string;
  /** Raw enum value from backend (e.g. `research_article`). */
  label?: string;
  /** Display-oriented label; derived from `label` only. */
  displayLabel?: string;
  confidence?: number;
  evidence: string[];
  reasoning?: string;
};

export type CandidateLabelView = {
  key: string;
  family: string;
  label: string;
  displayLabel: string;
  confidence: number;
};

/** Slim analysis_context strip — only fields the Classify tab is allowed to show. */
export type AnalysisSummaryView = {
  audience?: string;
  readiness?: string;
  routing?: string;
  reliability?: string;
  overallConfidence?: number;
  hasContent: boolean;
};

export type ClassificationViewModel = {
  decisions: ClassificationDecisionView[];
  candidates: CandidateLabelView[];
  keywords: string[];
  warnings: string[];
  processingTimeMs?: number;
  pipelineVersion?: string;
  analysisSummary: AnalysisSummaryView | null;
  /**
   * True when classification phase has anything displayable.
   * Sparse / all-`unknown` results with warnings still count as content (Ready).
   */
  hasContent: boolean;
};

function mapDecision(
  family: DecisionFamilyKey,
  familyTitle: string,
  raw: unknown,
): ClassificationDecisionView {
  const obj = isRecord(raw) ? raw : {};
  const label = asString(obj.label);
  return {
    family,
    familyTitle,
    label,
    displayLabel: label ? formatClassificationLabel(label) : undefined,
    confidence: asNumber(obj.confidence),
    evidence: asStringArray(obj.evidence),
    reasoning: asString(obj.reasoning),
  };
}

function mapCandidates(raw: unknown): CandidateLabelView[] {
  if (!isRecord(raw)) return [];
  const out: CandidateLabelView[] = [];
  for (const [key, val] of Object.entries(raw)) {
    const confidence = asNumber(val);
    if (confidence == null) continue;
    const dot = key.indexOf(".");
    const family = dot >= 0 ? key.slice(0, dot) : key;
    const label = dot >= 0 ? key.slice(dot + 1) : key;
    if (!label) continue;
    out.push({
      key,
      family,
      label,
      displayLabel: formatClassificationLabel(label),
      confidence,
    });
  }
  out.sort((a, b) => b.confidence - a.confidence || a.key.localeCompare(b.key));
  return out;
}

/**
 * Map optional `analysis_context` phase JSON into the Classify-tab summary strip.
 * Returns null if the payload is not a usable object.
 */
export function mapAnalysisSummary(
  result: PhaseResult | null | undefined,
): AnalysisSummaryView | null {
  if (!result || !isRecord(result)) return null;

  const documentProfile = isRecord(result.document_profile) ? result.document_profile : {};
  const analysisProfile = isRecord(result.analysis_profile) ? result.analysis_profile : {};
  const routingProfile = isRecord(result.routing_profile) ? result.routing_profile : {};
  const qualityProfile = isRecord(result.quality_profile) ? result.quality_profile : {};
  const confidence = isRecord(result.confidence) ? result.confidence : {};

  const view: AnalysisSummaryView = {
    audience: asString(documentProfile.intended_audience),
    readiness: asString(analysisProfile.readiness_level),
    routing: asString(routingProfile.primary_routing),
    reliability: asString(qualityProfile.reliability_level),
    overallConfidence: asNumber(confidence.overall),
    hasContent: false,
  };

  view.hasContent = Boolean(
    view.audience ||
      view.readiness ||
      view.routing ||
      view.reliability ||
      view.overallConfidence != null,
  );

  return view;
}

/**
 * Parse opaque classification (+ optional analysis_context) into a Classify-tab view model.
 * Returns null if `classification` is not a usable object.
 */
export function mapClassification(
  classification: PhaseResult | null | undefined,
  analysisContext?: PhaseResult | null | undefined,
): ClassificationViewModel | null {
  if (!classification || !isRecord(classification)) return null;

  const decisions = DECISION_FAMILIES.map(({ key, title }) =>
    mapDecision(key, title, classification[key]),
  );

  const candidates = mapCandidates(classification.candidate_labels);
  const keywords = asStringArray(classification.detected_keywords);
  const warnings = asStringArray(classification.warnings);
  const processingTimeMs = asNumber(classification.processing_time_ms);
  const pipelineVersion = asString(classification.pipeline_version);

  const analysisSummary = mapAnalysisSummary(analysisContext ?? null);
  const summary =
    analysisSummary && analysisSummary.hasContent ? analysisSummary : null;

  const hasDecision = decisions.some((d) => d.label != null || d.confidence != null);
  const hasContent = Boolean(
    hasDecision ||
      candidates.length ||
      keywords.length ||
      warnings.length ||
      processingTimeMs != null ||
      pipelineVersion ||
      summary,
  );

  return {
    decisions,
    candidates,
    keywords,
    warnings,
    processingTimeMs,
    pipelineVersion,
    analysisSummary: summary,
    hasContent,
  };
}
