import type { PaperAnalysis } from "@/types/api";

type AnalysisData = PaperAnalysis["data"];

// Maps the structured analysis object into the "## N. Heading" Markdown
// AnalysisOutput.tsx parses — numbered 1-16 for core fields (however many
// are actually present) and 17-30 for the medical-specific fields
// (backend/ai/prompts.py's MEDICAL_CORE_FIELDS + MEDICAL_*_FIELDS, grouped
// by document_type), matching AnalysisOutput's own hardcoded medical
// range exactly, so no changes are needed there to get the accordion/
// medical-badge treatment for real data.
const CORE_STRING_SECTIONS: { num: number; key: keyof AnalysisData; heading: string }[] = [
  { num: 1, key: "executive_summary", heading: "Executive Summary" },
  { num: 2, key: "abstract_explained", heading: "Abstract, Explained" },
  { num: 3, key: "research_objective", heading: "Research Objective" },
  { num: 4, key: "problem_statement", heading: "Problem Statement" },
  { num: 5, key: "methodology", heading: "Methodology" },
  { num: 6, key: "dataset", heading: "Dataset" },
  { num: 7, key: "experiments", heading: "Experiments" },
  { num: 8, key: "results", heading: "Results" },
];

// Core (17-19) is always-on whenever domain="medical". Only ONE of the
// three document-type-specific groups below is ever actually populated
// for a given analysis (backend/ai/prompts.py's medical_response_format()
// picks exactly one schema per call), so they safely reuse the same
// 20-26 number range — never more than one group's fields are truthy at
// once, so never more than one "## 20." etc. section actually renders.
const MEDICAL_STRING_SECTIONS: { num: number; key: keyof AnalysisData; heading: string }[] = [
  { num: 17, key: "clinical_relevance", heading: "Clinical Relevance (Medical)" },
  { num: 18, key: "clinical_translation", heading: "Clinical Translation (Medical)" },
  { num: 19, key: "clinical_bottom_line", heading: "Clinical Bottom Line (Medical)" },

  // document_type === "research"
  { num: 20, key: "pico_extraction", heading: "PICO Extraction (Medical)" },
  { num: 21, key: "evidence_quality", heading: "Evidence Quality (Medical)" },
  { num: 22, key: "risk_of_bias_assessment", heading: "Risk of Bias Assessment (Medical)" },
  { num: 23, key: "clinical_outcomes", heading: "Clinical Outcomes (Medical)" },
  { num: 24, key: "grade_assessment", heading: "GRADE Assessment (Medical)" },
  { num: 25, key: "patient_population", heading: "Patient Population (Medical)" },
  { num: 26, key: "ethics_patient_consent", heading: "Ethics & Patient Consent (Medical)" },

  // document_type === "clinical_guide"
  { num: 20, key: "target_audience", heading: "Target Audience (Medical)" },
  { num: 21, key: "scope_of_content", heading: "Scope of Content (Medical)" },
  { num: 22, key: "practical_value", heading: "Practical Value (Medical)" },
  { num: 23, key: "evidence_base", heading: "Evidence Base (Medical)" },
  { num: 24, key: "critical_assessment", heading: "Critical Assessment (Medical)" },
  { num: 25, key: "comparison_to_other_resources", heading: "Comparison to Other Resources (Medical)" },

  // document_type === "review"
  { num: 20, key: "review_coverage", heading: "Review Coverage (Medical)" },
  { num: 21, key: "search_strategy", heading: "Search Strategy (Medical)" },
  { num: 22, key: "quality_of_included_studies", heading: "Quality of Included Studies (Medical)" },
  { num: 23, key: "key_findings", heading: "Key Findings (Medical)" },
  { num: 24, key: "gaps_in_literature", heading: "Gaps in Literature (Medical)" },
  { num: 25, key: "future_research_directions", heading: "Future Research Directions (Medical)" },
];

const LIST_SECTIONS: { num: number; key: keyof AnalysisData; heading: string }[] = [
  { num: 9, key: "key_contributions", heading: "Key Contributions" },
  { num: 10, key: "strengths", heading: "Strengths" },
  { num: 11, key: "limitations", heading: "Limitations" },
  { num: 12, key: "future_work", heading: "Future Work" },
  { num: 13, key: "keywords", heading: "Keywords" },
];

export function analysisToMarkdown(data: AnalysisData): string {
  const parts: string[] = [];

  for (const { num, key, heading } of CORE_STRING_SECTIONS) {
    const value = data[key];
    if (typeof value === "string" && value.trim()) {
      parts.push(`## ${num}. ${heading}\n${value}`);
    }
  }

  for (const { num, key, heading } of LIST_SECTIONS) {
    const items = data[key];
    if (Array.isArray(items) && items.length) {
      parts.push(`## ${num}. ${heading}\n${items.map((item) => `- ${item}`).join("\n")}`);
    }
  }

  if (data.important_terms?.length) {
    const lines = data.important_terms.map((t) => `- **${t.term}**: ${t.definition}`);
    parts.push(`## 14. Important Terms\n${lines.join("\n")}`);
  }

  for (const { num, key, heading } of MEDICAL_STRING_SECTIONS) {
    const value = data[key];
    if (typeof value === "string" && value.trim()) {
      parts.push(`## ${num}. ${heading}\n${value}`);
    }
  }

  return parts.join("\n\n");
}
