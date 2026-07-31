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
  { key: "reporting_guideline", title: "Reporting" },
] as const;

export type DecisionFamilyKey = (typeof DECISION_FAMILIES)[number]["key"];

/** Identity strip order — Domain first for researcher scanning. */
export const PROFILE_FAMILY_ORDER: DecisionFamilyKey[] = [
  "domain",
  "document_type",
  "study_design",
  "reporting_guideline",
];

/** Below this, show as not confidently identified (still expandable in Details). */
export const CONFIDENCE_FLOOR = 0.4;

export type ConfidenceBand = "high" | "medium" | "low" | "none";

export function confidenceBand(n: number | undefined): ConfidenceBand {
  if (n == null || n <= 0) return "none";
  if (n >= 0.7) return "high";
  if (n >= 0.45) return "medium";
  return "low";
}

export function formatConfidenceBand(band: ConfidenceBand): string {
  switch (band) {
    case "high":
      return "High confidence";
    case "medium":
      return "Medium confidence";
    case "low":
      return "Low confidence";
    case "none":
      return "Not identified";
  }
}

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
  narrative_review: "Narrative Review",
  systematic_review: "Systematic Review",
  meta_analysis: "Meta-Analysis",
  clinical_guideline: "Clinical Guideline",
  research_article: "Research Article",
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
 * Display backend 0–1 confidence as percent (Details / power-user only).
 * Prefer {@link formatConfidenceBand} in primary Research Profile UI.
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

/** True when the decision has a usable label above the confidence floor. */
export function isConfidentDecision(d: ClassificationDecisionView): boolean {
  if (!d.label || /^(unknown|none|null|n\/a)$/i.test(d.label)) return false;
  if (d.confidence != null && d.confidence < CONFIDENCE_FLOOR) return false;
  return true;
}

/** Primary label for Research Profile rows — never "Unknown". */
export function profileDecisionLabel(d: ClassificationDecisionView): string {
  if (isConfidentDecision(d)) return d.displayLabel ?? formatClassificationLabel(d.label!);
  return "Not identified";
}

/** Weak backend guess shown only inside Why / Details — not as the hero label. */
export function profilePossibleLabel(d: ClassificationDecisionView): string | undefined {
  if (isConfidentDecision(d)) return undefined;
  if (d.label && !/^(unknown|none|null|n\/a)$/i.test(d.label)) {
    return d.displayLabel ?? formatClassificationLabel(d.label);
  }
  return undefined;
}

/** Strip enum namespaces and ML chrome from evidence lines. */
export function humanizeEvidenceLine(line: string): string {
  return line
    .replace(/\b(?:ScientificDomain|StudyDesign|DocumentType|ReportingGuideline)\./gi, "")
    .replace(/\bmatched signal\(s\)\b/gi, "supporting signals")
    .replace(/\bconfidence\s+0\.\d+\b/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

/** Researcher-facing summary under each identity row (not raw classifier prose). */
export function profileDecisionSummary(d: ClassificationDecisionView): string {
  const confident = isConfidentDecision(d);
  switch (d.family) {
    case "domain":
      return confident
        ? "Detected from terminology and subject matter throughout the manuscript."
        : "No research domain could be confidently detected.";
    case "document_type":
      return confident
        ? "How this manuscript presents itself as a scholarly document."
        : "Document type could not be confidently identified.";
    case "study_design":
      return confident
        ? "How the work appears to be organized methodologically."
        : "No study design could be confidently detected.";
    case "reporting_guideline":
      return confident
        ? "Reporting standard associated with this document type when present."
        : "No reporting guideline identified — common for many review and narrative papers.";
  }
}

export function orderedProfileDecisions(
  decisions: ClassificationDecisionView[],
): ClassificationDecisionView[] {
  const byFamily = new Map(decisions.map((d) => [d.family, d]));
  return PROFILE_FAMILY_ORDER.map((key) => byFamily.get(key)).filter(
    (d): d is ClassificationDecisionView => d != null,
  );
}

function joinNatural(parts: string[]): string {
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0]!;
  if (parts.length === 2) return `${parts[0]} and ${parts[1]}`;
  return `${parts.slice(0, -1).join(", ")}, and ${parts[parts.length - 1]}`;
}

/** Lowercase multi-word labels for prose; keep acronyms (RCT, CONSORT, AI/ML). */
function forProse(label: string): string {
  if (/^[A-Z0-9][A-Z0-9/+.-]*$/.test(label) && label.length <= 16) return label;
  return label.toLowerCase();
}

/**
 * Template Research Profile blurb from confident decisions + keywords.
 * Never invents labels the backend did not return (frontend-only, PR-B).
 */
export function buildProfileSummary(view: ClassificationViewModel): string | null {
  const byFamily = new Map(
    orderedProfileDecisions(view.decisions).map((d) => [d.family, d] as const),
  );
  const labelOf = (family: DecisionFamilyKey): string | undefined => {
    const d = byFamily.get(family);
    if (!d || !isConfidentDecision(d)) return undefined;
    return profileDecisionLabel(d);
  };

  const domain = labelOf("domain");
  const docType = labelOf("document_type");
  const design = labelOf("study_design");
  const reporting = labelOf("reporting_guideline");
  const topics = view.keywords
    .map((k) => k.trim())
    .filter(Boolean)
    .slice(0, 4);

  const sentences: string[] = [];

  if (docType && domain && design) {
    sentences.push(
      `This paper is a ${forProse(docType)} in ${forProse(domain)} (${forProse(design)}).`,
    );
  } else if (docType && domain) {
    sentences.push(`This paper is a ${forProse(docType)} in ${forProse(domain)}.`);
  } else if (docType && design) {
    sentences.push(
      `This paper is a ${forProse(docType)} with a ${forProse(design)} design.`,
    );
  } else if (docType) {
    sentences.push(`This paper presents as a ${forProse(docType)}.`);
  } else if (domain && design) {
    sentences.push(
      `This appears to be ${forProse(design)} work in ${forProse(domain)}.`,
    );
  } else if (domain) {
    sentences.push(`This paper is situated in ${forProse(domain)}.`);
  } else if (design) {
    sentences.push(`Study design looks like ${forProse(design)}.`);
  }

  if (topics.length > 0) {
    const focus = joinNatural(topics);
    if (sentences.length > 0) {
      sentences[0] = sentences[0]!.replace(/\.$/, "") + `, focused on ${focus}.`;
    } else {
      sentences.push(`Primary topics include ${focus}.`);
    }
  }

  const gaps: string[] = [];
  if (!design) gaps.push("no study design");
  if (!reporting) gaps.push("no reporting guideline");
  if (gaps.length > 0 && (docType || domain || design || topics.length > 0)) {
    const expected =
      docType && /review|guideline|editorial|opinion|perspective/i.test(docType)
        ? ", which is common for this document type"
        : "";
    const gapPhrase = gaps.length === 1 ? gaps[0]! : `${gaps[0]} and ${gaps[1]}`;
    const verb = gaps.length > 1 ? "were" : "was";
    sentences.push(
      `${gapPhrase.charAt(0).toUpperCase()}${gapPhrase.slice(1)} ${verb} detected${expected}.`,
    );
  }
  if (reporting && design) {
    sentences.push(`Reporting appears aligned with ${reporting}.`);
  } else if (reporting && !design) {
    sentences.push(`Reporting signals suggest ${reporting}.`);
  }

  if (sentences.length === 0) return null;
  return sentences.join(" ");
}

/**
 * Soft research-context line from analysis_context fields already on the view.
 * Does not invent Foundational/Applied stages — only rephrases readiness/routing.
 */
export function buildResearchContextLine(summary: AnalysisSummaryView | null): string | null {
  if (!summary?.hasContent) return null;
  const bits: string[] = [];
  if (summary.audience) {
    bits.push(`Intended for ${forProse(formatClassificationLabel(summary.audience))} readers`);
  }
  if (summary.readiness) {
    const ready = formatClassificationLabel(summary.readiness);
    bits.push(
      ready.toLowerCase().includes("fully")
        ? "analysis-ready"
        : ready.toLowerCase().includes("partial")
          ? "partially ready for deeper analysis"
          : ready.toLowerCase().includes("minimal")
            ? "minimally ready for analysis"
            : ready.toLowerCase().includes("not")
              ? "not yet ready for deep analysis"
              : `readiness: ${forProse(ready)}`,
    );
  }
  if (summary.routing) {
    bits.push(`routed as ${forProse(formatClassificationLabel(summary.routing))}`);
  }
  if (bits.length === 0) return null;
  if (bits.length === 1) return `${bits[0]!.charAt(0).toUpperCase()}${bits[0]!.slice(1)}.`;
  return `${bits[0]!.charAt(0).toUpperCase()}${bits[0]!.slice(1)}; ${bits.slice(1).join("; ")}.`;
}

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
