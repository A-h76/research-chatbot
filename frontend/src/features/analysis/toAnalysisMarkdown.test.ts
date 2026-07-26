import { describe, expect, it } from "vitest";
import { analysisToMarkdown } from "./toAnalysisMarkdown";
import type { PaperAnalysis } from "@/types/api";

type AnalysisData = PaperAnalysis["data"];

describe("analysisToMarkdown", () => {
  it("numbers core fields 1-13 and skips empty/absent ones", () => {
    const data: AnalysisData = {
      executive_summary: "A summary.",
      methodology: "Did stuff.",
      key_contributions: ["Contribution one"],
    };

    const md = analysisToMarkdown(data);

    expect(md).toContain("## 1. Executive Summary\nA summary.");
    expect(md).toContain("## 5. Methodology\nDid stuff.");
    expect(md).toContain("## 9. Key Contributions\n- Contribution one");
    // Absent/empty fields produce no section at all.
    expect(md).not.toContain("## 2.");
    expect(md).not.toContain("Abstract, Explained");
  });

  it("renders important_terms as a numbered section from the array shape", () => {
    const data: AnalysisData = {
      important_terms: [{ term: "RCT", definition: "Randomized controlled trial" }],
    };

    const md = analysisToMarkdown(data);

    expect(md).toContain("## 14. Important Terms\n- **RCT**: Randomized controlled trial");
  });

  it("numbers medical core fields 17-19, only when present", () => {
    const data: AnalysisData = {
      executive_summary: "A summary.",
      clinical_relevance: "Directly affects diagnosis.",
      clinical_bottom_line: "Trustworthy, would change practice.",
    };

    const md = analysisToMarkdown(data);

    expect(md).toContain("## 17. Clinical Relevance (Medical)\nDirectly affects diagnosis.");
    expect(md).toContain("## 19. Clinical Bottom Line (Medical)\nTrustworthy, would change practice.");
    // clinical_translation (18) wasn't set — no section for it, and no
    // document-type-specific (20+) fields either.
    expect(md).not.toContain("## 18.");
    expect(md).not.toContain("## 20.");
  });

  it("numbers the research document-type group 20-26, only when present", () => {
    const data: AnalysisData = {
      pico_extraction: "P: patients. I: drug. C: placebo. O: recovery.",
      grade_assessment: "High certainty.",
    };

    const md = analysisToMarkdown(data);

    expect(md).toContain("## 20. PICO Extraction (Medical)\nP: patients. I: drug. C: placebo. O: recovery.");
    expect(md).toContain("## 24. GRADE Assessment (Medical)\nHigh certainty.");
  });

  it("numbers the clinical_guide document-type group 20-25, only when present", () => {
    const data: AnalysisData = {
      target_audience: "General dentists and dental students.",
      comparison_to_other_resources: "Similar to standard endodontics textbooks.",
    };

    const md = analysisToMarkdown(data);

    expect(md).toContain("## 20. Target Audience (Medical)\nGeneral dentists and dental students.");
    expect(md).toContain(
      "## 25. Comparison to Other Resources (Medical)\nSimilar to standard endodontics textbooks."
    );
  });

  it("numbers the review document-type group 20-25, only when present", () => {
    const data: AnalysisData = {
      review_coverage: "Covers RCTs published 2010-2024.",
      future_research_directions: "Larger multi-center trials needed.",
    };

    const md = analysisToMarkdown(data);

    expect(md).toContain("## 20. Review Coverage (Medical)\nCovers RCTs published 2010-2024.");
    expect(md).toContain("## 25. Future Research Directions (Medical)\nLarger multi-center trials needed.");
  });

  it("returns an empty string for an empty analysis object", () => {
    expect(analysisToMarkdown({})).toBe("");
  });
});
