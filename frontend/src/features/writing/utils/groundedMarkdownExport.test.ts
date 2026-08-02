import { describe, expect, it } from "vitest";
import {
  buildLiteratureReviewMarkdown,
  computeExportTraceability,
} from "./groundedMarkdownExport";
import type { GroundedWritingResult } from "@/features/evidence/hooks/useGroundedWriting";

describe("buildLiteratureReviewMarkdown", () => {
  it("includes body, appendix, bibliography, and metadata", () => {
    const writing = {
      status: "ok",
      blocked_reason: null,
      mode: "grounded_v0",
      section_type: "literature_review",
      paragraph: "Benefit shown [#1].",
      citations: [],
      warnings: [],
      disclaimer: "Verify against sources.",
      bibliography: [
        {
          evidence_id: 1,
          page: 4,
          claim: "Drug X helps",
          quote: "significant reduction",
          confidence_band: "high",
          study_type: "RCT",
        },
      ],
      sections: [
        {
          id: "themes",
          title: "Themes",
          paragraph: "Benefit shown [#1].",
          citations: [],
          evidence_ids: [1],
          bindings: [
            {
              evidence_id: 1,
              page: 4,
              claim: "Drug X helps",
              quote: "significant reduction",
              confidence_band: "high",
              study_type: "RCT",
            },
          ],
          confidence: "high",
          status: "ok",
        },
      ],
      metrics: {
        grounding_pct: 1,
        citation_coverage: 1,
        unsupported_sentence_rate: 0,
        unsupported_claims: 0,
        paragraph_count: 1,
        evidence_linked_paragraphs: 1,
        unique_evidence_cited: 1,
        supporting_count: 1,
      },
      review: {
        status: "pass",
        pass_rate: 1,
        sections_checked: 1,
        sections_passed: 1,
        issue_count: 0,
        issues: [],
      },
    } as GroundedWritingResult;

    const md = buildLiteratureReviewMarkdown({
      title: "HbA1c review",
      body: "Benefit shown [#1].",
      writing,
      writing_version: "2.0.0",
      exported_at: "2026-07-29T12:00:00.000Z",
    });

    expect(md).toContain("# HbA1c review");
    expect(md).toContain("## Literature review");
    expect(md).toContain("## Evidence appendix");
    expect(md).toContain("### Evidence #1");
    expect(md).toContain("## Bibliography");
    expect(md).toContain("1. [#1] Drug X helps (p. 4)");
    expect(md).toContain("## Generation metadata");
    expect(md).toContain("evidence_traceability_100: yes");
    expect(computeExportTraceability(writing).meets_100).toBe(true);
  });

  it("fails meets_100 when orphan_ids present (parity with backend)", () => {
    const writing = {
      status: "ok",
      blocked_reason: null,
      mode: "grounded_v1",
      paragraph: "x [#99]",
      citations: [],
      warnings: [],
      disclaimer: "",
      sections: [
        {
          id: "themes",
          title: "Themes",
          paragraph: "x [#99]",
          citations: [],
          evidence_ids: [1],
          orphan_ids: [99],
          bindings: [{ evidence_id: 1, claim: "c", quote: "q" }],
          confidence: "high",
          status: "ok",
        },
      ],
    } as GroundedWritingResult;
    expect(computeExportTraceability(writing).meets_100).toBe(false);
  });

  it("canExportGroundedLitReview blocks on accept_allowed false", async () => {
    const { canExportGroundedLitReview } = await import("./groundedMarkdownExport");
    const gate = canExportGroundedLitReview({
      status: "ok",
      accept_allowed: false,
      blocked_reason: "reviewer_failed",
      mode: "grounded_v1",
      paragraph: "x",
      citations: [],
      warnings: [],
      disclaimer: "",
      sections: [],
    } as GroundedWritingResult);
    expect(gate.ok).toBe(false);
    expect(gate.reason).toMatch(/Reviewer/i);
  });

  it("canExportGroundedLitReview blocks on any severity=error (B-514)", async () => {
    const { canExportGroundedLitReview, reviewHasSeverityError } = await import(
      "./groundedMarkdownExport"
    );
    const writing = {
      status: "ok",
      accept_allowed: true,
      blocked_reason: null,
      mode: "grounded_v1",
      paragraph: "ok [#1].",
      citations: [],
      warnings: [],
      disclaimer: "",
      sections: [
        {
          id: "themes",
          title: "Themes",
          paragraph: "ok [#1].",
          citations: [],
          evidence_ids: [1],
          bindings: [{ evidence_id: 1, claim: "c", quote: "q" }],
          confidence: "high",
          status: "ok",
        },
      ],
      review: {
        status: "fail",
        pass_rate: 0,
        sections_checked: 1,
        sections_passed: 0,
        issue_count: 1,
        reviewer_version: "1.1.0",
        issues: [
          {
            code: "custom_error",
            severity: "error",
            section_id: "themes",
            message: "blocking",
          },
        ],
      },
    } as GroundedWritingResult;
    expect(reviewHasSeverityError(writing.review)).toBe(true);
    expect(canExportGroundedLitReview(writing).ok).toBe(false);
  });

  it("includes reviewer_version and issue_count in generation metadata", () => {
    const writing = {
      status: "ok",
      blocked_reason: null,
      mode: "grounded_v1",
      paragraph: "Benefit shown [#1].",
      citations: [],
      warnings: [],
      disclaimer: "Verify.",
      sections: [
        {
          id: "themes",
          title: "Themes",
          paragraph: "Benefit shown [#1].",
          citations: [],
          evidence_ids: [1],
          bindings: [{ evidence_id: 1, claim: "c", quote: "q" }],
          confidence: "high",
          status: "ok",
        },
      ],
      review: {
        status: "pass",
        pass_rate: 1,
        sections_checked: 1,
        sections_passed: 1,
        issue_count: 0,
        reviewer_version: "1.1.0",
        issues: [],
      },
    } as GroundedWritingResult;
    const md = buildLiteratureReviewMarkdown({
      title: "T",
      body: "Benefit shown [#1].",
      writing,
      writing_version: "2.0.0",
    });
    expect(md).toContain("reviewer_version: 1.1.0");
    expect(md).toContain("reviewer_issue_count: 0");
  });

  it("builds BibTeX from paper metadata on bindings", async () => {
    const { buildBibtexFromWriting } = await import("./groundedMarkdownExport");
    const bib = buildBibtexFromWriting({
      status: "ok",
      mode: "grounded_v1",
      writing_version: "2.0.0",
      section_type: "literature_review",
      paragraph: "x [#1]",
      citations: [],
      bibliography: [
        {
          evidence_id: 1,
          file_id: 9,
          page: 3,
          claim: "A claim",
          quote: "q",
          paper_title: "Transformers Are Great",
          authors: "Smith, A.; Jones, B.",
          year: "2020",
          venue: "Nature",
          doi: "10.1000/xyz",
        },
      ],
      sections: [],
      review: null,
      metrics: null,
      warnings: [],
      disclaimer: "",
      supporting_count: 1,
      blocked_reason: null,
    } as GroundedWritingResult);
    expect(bib).toContain("@article{");
    expect(bib).toContain("Transformers Are Great");
    expect(bib).toContain("10.1000/xyz");
    expect(bib).toContain("Dhund evidence #1");
  });
});
