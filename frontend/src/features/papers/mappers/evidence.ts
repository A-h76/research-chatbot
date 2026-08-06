/**
 * Evidence tab mapper — adapts Phase 1 `evidence_grading` (EvidenceGrades).
 *
 * Pattern: mapEvidence(phase) → EvidenceViewModel → PaperEvidenceTab
 * Components must not traverse raw phase JSON.
 */

import type { PhaseResult } from "@/features/pipeline";
import {
  asBoolean,
  asNumber,
  asString,
  asStringArray,
  cleanMarkdownArtifacts,
  formatConfidence,
  formatLabel,
  humanizeEnumKey,
  isRecord,
  normalizeEvidence,
  normalizeFrameworkId,
  type EvidenceRefView,
} from "./shared";

export type { EvidenceRefView };
export { formatConfidence, formatLabel, normalizeEvidence };

export type GradeView = {
  gradeType?: string;
  gradeValue?: string;
  displayValue?: string;
  description?: string;
  confidence?: number;
  framework?: string;
  rationale: string[];
  evidence: EvidenceRefView[];
};

export type FrameworkView = {
  key: string;
  framework: string;
  displayName: string;
  gradeValue?: string;
  displayGrade?: string;
  confidence?: number;
  summary?: string;
  /** GRADE-only metadata — omit comparing with Oxford scales. */
  evidenceQuality?: string;
  recommendationStrength?: string;
  downgradeFactors: string[];
  upgradeFactors: string[];
  initialQuality?: string;
  finalQuality?: string;
  evidence: EvidenceRefView[];
};

export type OutcomeGradeView = {
  key: string;
  outcomeName: string;
  gradeValue?: string;
  displayGrade?: string;
  confidence?: number;
  evidence: EvidenceRefView[];
};

export type RiskDomainView = {
  key: string;
  name: string;
  riskLevel?: string;
  supportText?: string;
};

export type RiskOfBiasView = {
  overallRisk?: string;
  assessmentTool?: string;
  confidence?: number;
  domains: RiskDomainView[];
  evidence: EvidenceRefView[];
};

export type ConsistencyView = {
  level?: string;
  score?: number;
  applicable?: boolean;
  confidence?: number;
  findings: string[];
  evidence: EvidenceRefView[];
};

export type PrecisionView = {
  level?: string;
  score?: number;
  confidence?: number;
  sampleSize?: number;
  effectSizeLabel?: string;
  confidenceIntervalLabel?: string;
  evidence: EvidenceRefView[];
};

export type DirectnessView = {
  level?: string;
  score?: number;
  confidence?: number;
  populationMatch?: number;
  interventionMatch?: number;
  comparatorMatch?: number;
  outcomeMatch?: number;
  evidence: EvidenceRefView[];
};

export type PublicationBiasView = {
  riskLevel?: string;
  applicable?: boolean;
  confidence?: number;
  evidence: EvidenceRefView[];
};

export type ReportingQualityView = {
  score?: number;
  guideline?: string;
  confidence?: number;
  missingItems: string[];
  evidence: EvidenceRefView[];
};

export type AssessmentsView = {
  riskOfBias?: RiskOfBiasView;
  consistency?: ConsistencyView;
  precision?: PrecisionView;
  directness?: DirectnessView;
  publicationBias?: PublicationBiasView;
  reportingQuality?: ReportingQualityView;
};

export type EvidenceViewModel = {
  skipped: boolean;
  /** Researcher-facing skip explanation (never raw routing jargon). */
  skipReason?: string;
  /** Short title for the skipped state. */
  skipTitle?: string;
  hasContent: boolean;
  overallGrade: GradeView | null;
  studyQuality?: string;
  frameworks: FrameworkView[];
  outcomeGrades: OutcomeGradeView[];
  assessments: AssessmentsView;
  summaryConfidence?: number;
  warnings: string[];
  errors: string[];
};

/**
 * Turn pipeline skip `reasoning` into calm researcher copy.
 * Raw strings like "routing profile does not include evidence_grading" stay out of the UI.
 */
export function humanizeEvidenceSkipReason(raw: string | undefined): {
  title: string;
  detail: string;
} {
  const text = (raw ?? "").trim().toLowerCase();
  if (!text) {
    return {
      title: "Not Assessed",
      detail:
        "No statistical evidence extraction or formal evidence grade is available for this paper yet. Chat and extract tools can still use the manuscript text.",
    };
  }
  if (
    text.includes("routing profile") ||
    text.includes("not required") ||
    text.includes("does not include evidence_grading") ||
    text.includes("formal evidence grading was not run") ||
    text.includes("narrative reviews, editorials")
  ) {
    return {
      title: "Not Assessed",
      detail:
        "No statistical evidence extraction is currently supported for this document type. Formal grading (study quality, GRADE-style frameworks) is typically reserved for clinical trials and systematic reviews.",
    };
  }
  if (text.includes("skipped") || text.includes("insufficient") || text.includes("too little")) {
    return {
      title: "Not Assessed",
      detail:
        "There was not enough structured evidence signal to produce a reliable grade for this paper.",
    };
  }
  // Unknown backend copy — keep readable, strip snake_case module ids.
  const cleaned = raw!
    .replace(/\bevidence_grading\b/gi, "evidence grading")
    .replace(/\brouting profile\b/gi, "analysis plan")
    .replace(/_/g, " ")
    .trim();
  return {
    title: "Not Assessed",
    detail: cleaned.charAt(0).toUpperCase() + cleaned.slice(1),
  };
}

function mapGrade(raw: unknown): GradeView | null {
  if (!isRecord(raw)) return null;
  const gradeValue = asString(raw.grade_value);
  const descriptionRaw = asString(raw.grade_description);
  const rationale: string[] = [];
  if (Array.isArray(raw.rationale)) {
    for (const r of raw.rationale) {
      if (!isRecord(r)) continue;
      const reasoning = asString(r.reasoning);
      if (reasoning) rationale.push(cleanMarkdownArtifacts(reasoning));
    }
  }
  const framework = asString(raw.framework);
  return {
    gradeType: asString(raw.grade_type),
    gradeValue,
    displayValue: gradeValue ? formatLabel(gradeValue) : undefined,
    description: descriptionRaw ? cleanMarkdownArtifacts(descriptionRaw) : undefined,
    confidence: asNumber(raw.confidence),
    framework: framework ? normalizeFrameworkId(framework) : undefined,
    rationale,
    evidence: normalizeEvidence(raw.evidence),
  };
}

function mapFrameworks(raw: unknown): FrameworkView[] {
  if (!isRecord(raw)) return [];
  const out: FrameworkView[] = [];
  for (const [uglyKey, val] of Object.entries(raw)) {
    if (!isRecord(val)) continue;
    const nestedId = asString(val.framework);
    const framework = normalizeFrameworkId(nestedId ?? uglyKey);
    const grade = isRecord(val.grade) ? val.grade : {};
    const gradeValue = asString(grade.grade_value);
    const gradeResult = isRecord(val.grade_result) ? val.grade_result : null;
    const desc = asString(grade.grade_description);
    const summaryParts: string[] = [];
    if (desc) summaryParts.push(cleanMarkdownArtifacts(desc));
    if (gradeResult) {
      const eq = asString(gradeResult.evidence_quality);
      const rs = asString(gradeResult.recommendation_strength);
      if (eq) summaryParts.push(`Evidence quality: ${formatLabel(eq)}`);
      if (rs) summaryParts.push(`Recommendation: ${formatLabel(rs)}`);
    }

    out.push({
      key: `framework:${framework}`,
      framework,
      displayName: framework.toUpperCase() === "GRADE" ? "GRADE" : formatLabel(framework),
      gradeValue,
      displayGrade: gradeValue
        ? framework === "oxford" || framework === "sign"
          ? gradeValue
          : formatLabel(gradeValue)
        : undefined,
      confidence: asNumber(val.confidence) ?? asNumber(grade.confidence),
      summary: summaryParts.length ? summaryParts.join(" · ") : undefined,
      evidenceQuality: gradeResult ? asString(gradeResult.evidence_quality) : undefined,
      recommendationStrength: gradeResult
        ? asString(gradeResult.recommendation_strength)
        : undefined,
      downgradeFactors: gradeResult
        ? asStringArray(gradeResult.downgrade_factors).map((f) => formatLabel(f))
        : [],
      upgradeFactors: gradeResult
        ? asStringArray(gradeResult.upgrade_factors).map((f) => formatLabel(f))
        : [],
      initialQuality: gradeResult ? asString(gradeResult.initial_quality) : undefined,
      finalQuality: gradeResult ? asString(gradeResult.final_quality) : undefined,
      evidence: normalizeEvidence(val.evidence),
    });
  }
  // Stable order: grade, oxford, then others alpha
  const order = (id: string) => (id === "grade" ? 0 : id === "oxford" ? 1 : 10);
  out.sort((a, b) => order(a.framework) - order(b.framework) || a.framework.localeCompare(b.framework));
  return out;
}

function mapOutcomeGrades(raw: unknown): OutcomeGradeView[] {
  if (!isRecord(raw)) return [];
  const out: OutcomeGradeView[] = [];
  for (const [name, val] of Object.entries(raw)) {
    if (!isRecord(val)) continue;
    const outcomeName = asString(val.outcome_name) ?? name;
    const grade = isRecord(val.grade) ? val.grade : {};
    const gradeValue = asString(grade.grade_value);
    out.push({
      key: `outcome:${outcomeName}`,
      outcomeName,
      gradeValue,
      displayGrade: gradeValue ? formatLabel(gradeValue) : undefined,
      confidence: asNumber(val.confidence) ?? asNumber(grade.confidence),
      evidence: normalizeEvidence(val.evidence),
    });
  }
  out.sort((a, b) => a.outcomeName.localeCompare(b.outcomeName));
  return out;
}

function mapRiskOfBias(raw: unknown): RiskOfBiasView | undefined {
  if (!isRecord(raw)) return undefined;
  const overallRisk = asString(raw.overall_risk);
  const domainsRaw = isRecord(raw.domains) ? raw.domains : {};
  const domains: RiskDomainView[] = Object.entries(domainsRaw).map(([k, v]) => {
    const d = isRecord(v) ? v : {};
    return {
      key: k,
      name: humanizeEnumKey(k),
      riskLevel: asString(d.risk_level),
      supportText: asString(d.support_text),
    };
  });
  domains.sort((a, b) => a.name.localeCompare(b.name));

  const available =
    (overallRisk != null && overallRisk !== "unknown") || domains.length > 0;
  if (!available) return undefined;

  return {
    overallRisk,
    assessmentTool: asString(raw.assessment_tool),
    confidence: asNumber(raw.confidence),
    domains,
    evidence: normalizeEvidence(raw.evidence),
  };
}

function mapConsistency(raw: unknown): ConsistencyView | undefined {
  if (!isRecord(raw)) return undefined;
  const level = asString(raw.consistency_level);
  const applicable = asBoolean(raw.applicable);
  const findings = asStringArray(raw.findings);
  if (applicable === false && (level === "unavailable" || level === "unknown" || !level)) {
    return undefined;
  }
  if (!level && applicable !== true && findings.length === 0) return undefined;
  return {
    level,
    score: asNumber(raw.consistency_score),
    applicable,
    confidence: asNumber(raw.confidence),
    findings,
    evidence: normalizeEvidence(raw.evidence),
  };
}

function mapPrecision(raw: unknown): PrecisionView | undefined {
  if (!isRecord(raw)) return undefined;
  const level = asString(raw.precision_level);
  const effect = isRecord(raw.effect_size) ? raw.effect_size : null;
  const ci = isRecord(raw.confidence_interval) ? raw.confidence_interval : null;
  let effectSizeLabel: string | undefined;
  if (effect) {
    const mt = asString(effect.measure_type);
    const val = asNumber(effect.value);
    if (mt || val != null) {
      effectSizeLabel = [mt ? formatLabel(mt) : null, val != null ? String(val) : null]
        .filter(Boolean)
        .join(": ");
    }
  }
  let confidenceIntervalLabel: string | undefined;
  if (ci) {
    const lower = asNumber(ci.lower);
    const upper = asNumber(ci.upper);
    const levelCi = asNumber(ci.level);
    if (lower != null && upper != null) {
      confidenceIntervalLabel = `${lower}–${upper}${
        levelCi != null ? ` (${Math.round(levelCi * 100)}% CI)` : ""
      }`;
    }
  }
  if (
    (!level || level === "unknown" || level === "unavailable") &&
    !effectSizeLabel &&
    !confidenceIntervalLabel &&
    asNumber(raw.sample_size) == null
  ) {
    return undefined;
  }
  return {
    level,
    score: asNumber(raw.precision_score),
    confidence: asNumber(raw.confidence),
    sampleSize: asNumber(raw.sample_size),
    effectSizeLabel,
    confidenceIntervalLabel,
    evidence: normalizeEvidence(raw.evidence),
  };
}

function mapDirectness(raw: unknown): DirectnessView | undefined {
  if (!isRecord(raw)) return undefined;
  const level = asString(raw.directness_level);
  if (!level || level === "unknown") return undefined;
  return {
    level,
    score: asNumber(raw.directness_score),
    confidence: asNumber(raw.confidence),
    populationMatch: asNumber(raw.population_match),
    interventionMatch: asNumber(raw.intervention_match),
    comparatorMatch: asNumber(raw.comparator_match),
    outcomeMatch: asNumber(raw.outcome_match),
    evidence: normalizeEvidence(raw.evidence),
  };
}

function mapPublicationBias(raw: unknown): PublicationBiasView | undefined {
  if (raw == null) return undefined;
  if (!isRecord(raw)) return undefined;
  const applicable = asBoolean(raw.applicable);
  const riskLevel = asString(raw.risk_level);
  if (applicable === false && (riskLevel === "unknown" || !riskLevel)) {
    return undefined;
  }
  return {
    riskLevel,
    applicable,
    confidence: asNumber(raw.confidence),
    evidence: normalizeEvidence(raw.evidence),
  };
}

function mapReportingQuality(raw: unknown): ReportingQualityView | undefined {
  if (!isRecord(raw)) return undefined;
  const score = asNumber(raw.reporting_quality_score);
  const guideline = asString(raw.reporting_guideline);
  if (score == null && (!guideline || guideline === "unknown")) return undefined;
  return {
    score,
    guideline: guideline && guideline !== "unknown" ? guideline : undefined,
    confidence: asNumber(raw.confidence),
    missingItems: asStringArray(raw.missing_items).map((i) => formatLabel(i)),
    evidence: normalizeEvidence(raw.evidence),
  };
}

function errorMessages(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  const out: string[] = [];
  for (const item of raw) {
    if (typeof item === "string" && item.trim()) {
      out.push(cleanMarkdownArtifacts(item));
      continue;
    }
    if (!isRecord(item)) continue;
    const msg = asString(item.message);
    const component = asString(item.component);
    if (msg && component) out.push(cleanMarkdownArtifacts(`${component}: ${msg}`));
    else if (msg) out.push(cleanMarkdownArtifacts(msg));
  }
  return out;
}

/**
 * Adapt opaque evidence_grading phase JSON into EvidenceViewModel.
 */
export function mapEvidence(phase: PhaseResult | null | undefined): EvidenceViewModel | null {
  if (!phase || !isRecord(phase)) return null;

  const skipped = phase.skipped === true;
  const skipCopy = skipped ? humanizeEvidenceSkipReason(asString(phase.reasoning)) : null;
  const warnings = asStringArray(phase.warnings).map(cleanMarkdownArtifacts);
  const errors = errorMessages(phase.errors);

  const confidenceObj = isRecord(phase.confidence) ? phase.confidence : {};
  const summaryConfidence = asNumber(confidenceObj.overall);

  const overallGrade = mapGrade(phase.overall_grade);
  const studyQuality = asString(phase.study_quality);
  const frameworks = mapFrameworks(phase.framework_results);
  const outcomeGrades = mapOutcomeGrades(phase.outcome_grades);

  const assessments: AssessmentsView = {
    riskOfBias: mapRiskOfBias(phase.risk_of_bias),
    consistency: mapConsistency(phase.consistency),
    precision: mapPrecision(phase.precision),
    directness: mapDirectness(phase.directness),
    publicationBias: mapPublicationBias(phase.publication_bias),
    reportingQuality: mapReportingQuality(phase.reporting_quality),
  };

  const hasAssessment = Boolean(
    assessments.riskOfBias ||
      assessments.consistency ||
      assessments.precision ||
      assessments.directness ||
      assessments.publicationBias ||
      assessments.reportingQuality,
  );

  const hasGroupContent = Boolean(
    (overallGrade && (overallGrade.gradeValue || overallGrade.description)) ||
      (studyQuality && studyQuality !== "unknown") ||
      frameworks.length ||
      outcomeGrades.length ||
      hasAssessment ||
      summaryConfidence != null ||
      warnings.length ||
      errors.length ||
      asString(phase.pipeline_version),
  );

  const hasContent = skipped || hasGroupContent || phase.skipped === false;

  return {
    skipped,
    skipReason: skipCopy?.detail,
    skipTitle: skipCopy?.title,
    hasContent,
    overallGrade,
    studyQuality,
    frameworks,
    outcomeGrades,
    assessments,
    summaryConfidence,
    warnings,
    errors,
  };
}
