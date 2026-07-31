import { describe, expect, it } from "vitest";
import type { DocumentUnderstandingView } from "../mappers/structure";
import {
  buildDocumentAnalysisReport,
  isProcessingProblemMessage,
  parseMissingSectionWarning,
} from "./documentAnalysis";

function baseView(over: Partial<DocumentUnderstandingView> = {}): DocumentUnderstandingView {
  return {
    authors: [],
    sections: [],
    warnings: [],
    errors: [],
    quality: {},
    hasContent: true,
    ...over,
  };
}

describe("documentAnalysis", () => {
  it("parses missing IMRaD section warnings", () => {
    expect(parseMissingSectionWarning("No 'methods' section detected.")).toBe("methods");
    expect(parseMissingSectionWarning("No 'abstract' section detected.")).toBe("abstract");
    expect(parseMissingSectionWarning("Low figure contrast")).toBeNull();
  });

  it("treats OCR/scanned messages as processing problems", () => {
    expect(isProcessingProblemMessage("No extractable text found on any of 5 page(s)")).toBe(
      true,
    );
    expect(isProcessingProblemMessage("No 'methods' section detected.")).toBe(false);
  });

  it("presents review-like papers as narrative structure, not warnings", () => {
    const report = buildDocumentAnalysisReport(
      baseView({
        title: "Kupffer cells",
        wordCount: 8000,
        referenceCount: 40,
        quality: {
          ocr_quality: 1,
          extraction_quality: 1,
          metadata_quality: 0.86,
          section_quality: 0.14,
          completeness: 0.5,
        },
        warnings: [
          "No 'abstract' section detected.",
          "No 'methods' section detected.",
          "No 'results' section detected.",
        ],
        sections: [
          { heading: "1. Introduction", sectionType: "introduction" },
          { heading: "2. Origin and heterogeneity of KCs", sectionType: "other" },
          { heading: "3. Functions in homeostasis", sectionType: "other" },
          { heading: "References", sectionType: "references" },
        ],
      }),
    );

    expect(report.structureKind).toBe("narrative_review");
    expect(report.overallLabel).toBe("Excellent");
    expect(report.processingProblems).toEqual([]);
    expect(report.notDetected).toEqual(expect.arrayContaining(["Methods", "Results"]));
    expect(report.detected).toEqual(
      expect.arrayContaining(["Introduction", "Thematic sections", "References"]),
    );
    expect(report.whyExplanation).toMatch(/themes/i);
    expect(report.processingSignals.some((s) => s.label.includes("OCR") && s.ok)).toBe(true);
  });

  it("keeps real extraction failures as processing issues", () => {
    const report = buildDocumentAnalysisReport(
      baseView({
        errors: ["No extractable text found — this document may be a scanned/image-only PDF."],
        quality: { ocr_quality: 0 },
      }),
    );
    expect(report.overallLabel).toBe("Needs attention");
    expect(report.processingProblems[0]).toMatch(/scanned/i);
  });

  it("uses classification document type when provided", () => {
    const report = buildDocumentAnalysisReport(
      baseView({
        warnings: ["No 'methods' section detected.", "No 'results' section detected."],
        sections: [
          { heading: "Introduction", sectionType: "introduction" },
          { heading: "Theme A", sectionType: "other" },
        ],
      }),
      { documentTypeLabel: "Review Article" },
    );
    expect(report.structureTitle).toMatch(/Review/i);
  });
});
