/**
 * Structure-tab Document Analysis presentation.
 * Backend quality warnings stay as-is; this layer educates instead of alarming
 * when a paper simply isn't IMRaD (e.g. narrative reviews).
 */

import type { DocumentUnderstandingView } from "../mappers/structure";

const MISSING_SECTION_RE = /^No ['"]?(\w+)['"]? section detected\.?\s*$/i;

/** Genuine processing problems — keep amber/red treatment. */
const PROCESSING_PROBLEM_RE =
  /\b(ocr|scanned|image-only|extractable text|garbled|corrupted|unreadable|missing page|pages?\)|doi not found|broken encoding)\b/i;

const IMRAD_CORE = ["abstract", "methods", "results", "discussion"] as const;
type ImradCore = (typeof IMRAD_CORE)[number];

export type ProcessingSignal = {
  id: string;
  label: string;
  detail?: string;
  ok: boolean;
};

export type StructureProfileKind =
  | "imrad"
  | "narrative_review"
  | "partial_imrad"
  | "unknown";

export type DocumentAnalysisReport = {
  overallLabel: string;
  overallDetail: string;
  processingSignals: ProcessingSignal[];
  /** Real failures — orange/red. */
  processingProblems: string[];
  structureKind: StructureProfileKind;
  structureTitle: string;
  structureSummary: string;
  whyExplanation?: string;
  detected: string[];
  notDetected: string[];
  expectedOutline: string[];
  /** Informational notes that are not processing failures. */
  structureNotes: string[];
  show: boolean;
};

function normType(t: string | undefined): string {
  return (t ?? "").trim().toLowerCase();
}

function presentTypes(view: DocumentUnderstandingView): Set<string> {
  const types = new Set<string>();
  for (const s of view.sections) {
    const t = normType(s.sectionType);
    if (t && t !== "other" && t !== "unknown" && t !== "misc") types.add(t);
  }
  if (view.abstract) types.add("abstract");
  if ((view.referenceCount ?? 0) > 0 || view.references.length > 0) types.add("references");
  // Heading text fallback when type is other/missing
  for (const s of view.sections) {
    const h = s.heading.trim().toLowerCase();
    if (/^(\d+(\.\d+)*\.?\s+)?introduction\b/.test(h)) types.add("introduction");
    if (/\breferences?\b|\bbibliography\b/.test(h)) types.add("references");
    if (/^abstract$|^a\s+b\s+s\s+t\s+r\s+a\s+c\s+t$/i.test(h.replace(/\s+/g, " ").trim())) {
      types.add("abstract");
    }
  }
  return types;
}

function thematicSectionCount(view: DocumentUnderstandingView): number {
  return view.sections.filter((s) => {
    const t = normType(s.sectionType);
    return !t || t === "other" || t === "unknown";
  }).length;
}

export function parseMissingSectionWarning(msg: string): ImradCore | null {
  const m = MISSING_SECTION_RE.exec(msg.trim());
  if (!m) return null;
  const key = m[1]!.toLowerCase();
  return (IMRAD_CORE as readonly string[]).includes(key) ? (key as ImradCore) : null;
}

export function isProcessingProblemMessage(msg: string): boolean {
  if (parseMissingSectionWarning(msg)) return false;
  return PROCESSING_PROBLEM_RE.test(msg) || /failed|error|could not|unable to/i.test(msg);
}

function scoreBand(n: number | undefined): "excellent" | "good" | "fair" | "weak" | "unknown" {
  if (n == null) return "unknown";
  if (n >= 0.85) return "excellent";
  if (n >= 0.7) return "good";
  if (n >= 0.45) return "fair";
  return "weak";
}

function bandLabel(band: ReturnType<typeof scoreBand>): string {
  switch (band) {
    case "excellent":
      return "Excellent";
    case "good":
      return "Good";
    case "fair":
      return "Fair";
    case "weak":
      return "Needs attention";
    default:
      return "—";
  }
}

export function inferStructureProfile(
  view: DocumentUnderstandingView,
  missingFromWarnings: ImradCore[],
  documentTypeLabel?: string | null,
): Pick<
  DocumentAnalysisReport,
  | "structureKind"
  | "structureTitle"
  | "structureSummary"
  | "whyExplanation"
  | "detected"
  | "notDetected"
  | "expectedOutline"
> {
  const types = presentTypes(view);
  const missing = new Set(missingFromWarnings);
  for (const core of IMRAD_CORE) {
    if (!types.has(core)) missing.add(core);
    else missing.delete(core);
  }

  // Metadata abstract counts even when section heading wasn't normalized.
  if (view.abstract) missing.delete("abstract");

  const hasIntro = types.has("introduction");
  const hasRefs = types.has("references");
  const thematic = thematicSectionCount(view);
  const missingMethodsResults = missing.has("methods") && missing.has("results");
  const typeHint = (documentTypeLabel ?? "").toLowerCase();
  const classifiedReview =
    /\breview\b|\bsurvey\b|\bnarrative\b|\bperspective\b|\beditorial\b|\bcommentary\b/.test(
      typeHint,
    );

  const looksLikeNarrativeReview =
    classifiedReview ||
    (missingMethodsResults && (hasIntro || thematic >= 2) && view.sections.length >= 2);

  const detected: string[] = [];
  if (hasIntro) detected.push("Introduction");
  if (types.has("abstract") || view.abstract) detected.push("Abstract");
  if (thematic >= 1 && looksLikeNarrativeReview) detected.push("Thematic sections");
  if (types.has("methods")) detected.push("Methods");
  if (types.has("results")) detected.push("Results");
  if (types.has("discussion")) detected.push("Discussion");
  if (hasRefs) detected.push("References");
  // Fall back: list a few non-IMRaD headings as thematic evidence
  if (looksLikeNarrativeReview && !detected.includes("Thematic sections") && thematic >= 1) {
    detected.push("Thematic sections");
  }

  const notDetected = [...missing].map(
    (k) => k.charAt(0).toUpperCase() + k.slice(1),
  );

  if (looksLikeNarrativeReview) {
    return {
      structureKind: "narrative_review",
      structureTitle: classifiedReview
        ? documentTypeLabel!.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
        : "Narrative review structure",
      structureSummary:
        "This document does not follow the standard IMRaD research-paper layout (Introduction · Methods · Results · Discussion).",
      whyExplanation:
        "This article appears to organize content by themes rather than Methods/Results. That is common for review and perspective papers — no action required.",
      detected,
      notDetected,
      expectedOutline: ["Introduction", "Thematic sections", "References"],
    };
  }

  if (missing.size === 0) {
    return {
      structureKind: "imrad",
      structureTitle: "IMRaD research paper",
      structureSummary: "Canonical research sections were detected.",
      whyExplanation: undefined,
      detected,
      notDetected: [],
      expectedOutline: ["Abstract", "Introduction", "Methods", "Results", "Discussion", "References"],
    };
  }

  if (missing.size <= 2 && (types.has("methods") || types.has("results") || types.has("discussion"))) {
    return {
      structureKind: "partial_imrad",
      structureTitle: "Partial IMRaD structure",
      structureSummary:
        "Some standard research sections were found; others were not labeled in the PDF headings.",
      whyExplanation:
        "Missing labels often mean the PDF uses different heading wording, not that the paper failed to process.",
      detected,
      notDetected,
      expectedOutline: ["Abstract", "Introduction", "Methods", "Results", "Discussion", "References"],
    };
  }

  return {
    structureKind: "unknown",
    structureTitle: "Non-standard structure",
    structureSummary:
      "Heading layout does not closely match a standard IMRaD research paper.",
    whyExplanation:
      "Dhund still extracted text and sections; the labels below only describe how headings compare to a typical experimental paper.",
    detected,
    notDetected,
    expectedOutline: ["Introduction", "Body sections", "References"],
  };
}

export function buildDocumentAnalysisReport(
  view: DocumentUnderstandingView,
  opts?: { documentTypeLabel?: string | null },
): DocumentAnalysisReport {
  const missingFromWarnings: ImradCore[] = [];
  const processingProblems: string[] = [...view.errors];
  const leftoverNotes: string[] = [];

  for (const w of view.warnings) {
    const missing = parseMissingSectionWarning(w);
    if (missing) {
      missingFromWarnings.push(missing);
      continue;
    }
    if (isProcessingProblemMessage(w)) {
      processingProblems.push(w);
      continue;
    }
    leftoverNotes.push(w);
  }

  const q = view.quality;
  const ocrBand = scoreBand(q.ocr_quality);
  const extractBand = scoreBand(q.extraction_quality);
  const metaBand = scoreBand(q.metadata_quality);

  const processingSignals: ProcessingSignal[] = [];
  if (q.ocr_quality != null) {
    processingSignals.push({
      id: "ocr",
      label: ocrBand === "excellent" || ocrBand === "good" ? "OCR successful" : "OCR quality",
      detail: bandLabel(ocrBand),
      ok: ocrBand === "excellent" || ocrBand === "good",
    });
  } else if (!view.errors.some((e) => /ocr|scanned|extractable/i.test(e))) {
    processingSignals.push({
      id: "ocr",
      label: "Text extracted",
      detail: view.wordCount != null ? `${view.wordCount.toLocaleString()} words` : undefined,
      ok: (view.wordCount ?? 0) > 0 || view.sections.length > 0,
    });
  }

  if (q.extraction_quality != null) {
    processingSignals.push({
      id: "extraction",
      label:
        extractBand === "excellent" || extractBand === "good"
          ? "Extraction successful"
          : "Extraction quality",
      detail: bandLabel(extractBand),
      ok: extractBand === "excellent" || extractBand === "good",
    });
  }

  const hasMeta =
    Boolean(view.title || view.authors.length || view.doi || view.abstract) ||
    (q.metadata_quality != null && q.metadata_quality >= 0.5);
  processingSignals.push({
    id: "metadata",
    label: hasMeta ? "Metadata extracted" : "Metadata limited",
    detail: q.metadata_quality != null ? bandLabel(metaBand) : undefined,
    ok: hasMeta,
  });

  const hasRefs =
    view.references.length > 0 ||
    (view.referenceCount ?? 0) > 0 ||
    view.sections.some((s) => /reference|bibliograph/i.test(s.heading) || normType(s.sectionType) === "references");
  processingSignals.push({
    id: "references",
    label: hasRefs ? "References detected" : "References not labeled",
    ok: hasRefs,
  });

  const profile = inferStructureProfile(view, missingFromWarnings, opts?.documentTypeLabel);

  const hasHardProblems = processingProblems.length > 0 || processingSignals.some((s) => !s.ok && s.id === "ocr");
  const processingStrong = processingSignals.filter((s) => s.ok).length >= 2 && !hasHardProblems;

  let overallLabel = "Good";
  let overallDetail = "Document understanding completed.";
  if (hasHardProblems) {
    overallLabel = "Needs attention";
    overallDetail = "One or more processing issues need a look.";
  } else if (processingStrong) {
    overallLabel = "Excellent";
    overallDetail =
      profile.structureKind === "narrative_review"
        ? "Processed successfully — structure differs from IMRaD, which is expected for many reviews."
        : "Text, metadata, and structure signals look healthy.";
  }

  const show =
    processingSignals.length > 0 ||
    processingProblems.length > 0 ||
    profile.notDetected.length > 0 ||
    leftoverNotes.length > 0 ||
    view.sections.length > 0 ||
    Object.values(q).some((v) => v != null);

  return {
    overallLabel,
    overallDetail,
    processingSignals,
    processingProblems,
    ...profile,
    structureNotes: leftoverNotes,
    show,
  };
}
