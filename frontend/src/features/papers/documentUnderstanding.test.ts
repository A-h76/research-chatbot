import { describe, it, expect } from "vitest";
import { mapStructure, parseDocumentUnderstanding, formatQualityScore } from "./mappers/structure";
import type { PhaseResult } from "@/features/pipeline";

const SAMPLE: PhaseResult = {
  id: "doc-1",
  metadata: {
    title: "A Study of Widgets",
    authors: ["Ada Lovelace", "Alan Turing"],
    journal: "Nature Methods",
    venue: "",
    publication_year: 2024,
    language: "en",
    doi: "10.1000/xyz",
    abstract: "We study widgets.",
  },
  structure: {
    heading_order: ["Introduction", "Methods"],
    raw_headings: {
      Introduction: "Widgets matter.",
      Methods: "We measured things.",
    },
    section_types: {
      Introduction: "introduction",
      Methods: "methods",
    },
    references: [],
  },
  statistics: {
    word_count: 1200,
    page_count: 8,
    section_count: 2,
  },
  quality: {
    extraction_quality: 0.9,
    confidence: 0.85,
    warnings: ["Low figure contrast"],
    errors: [],
  },
};

describe("mapStructure", () => {
  it("returns null for non-objects", () => {
    expect(mapStructure(null)).toBeNull();
    expect(parseDocumentUnderstanding(undefined)).toBeNull();
  });

  it("maps bibliographic and structure fields without inventing values", () => {
    const view = mapStructure(SAMPLE)!;
    expect(view.title).toBe("A Study of Widgets");
    expect(view.authors).toEqual(["Ada Lovelace", "Alan Turing"]);
    expect(view.journal).toBe("Nature Methods");
    expect(view.publicationYear).toBe(2024);
    expect(view.language).toBe("en");
    expect(view.wordCount).toBe(1200);
    expect(view.pageCount).toBe(8);
    expect(view.sections).toHaveLength(2);
    expect(view.sections[0]).toMatchObject({
      heading: "Introduction",
      sectionType: "introduction",
      content: "Widgets matter.",
    });
    expect(view.references).toEqual([]);
    expect(view.warnings).toEqual(["Low figure contrast"]);
    expect(view.quality.extraction_quality).toBe(0.9);
    expect(view.hasContent).toBe(true);
  });

  it("marks empty payloads as no content", () => {
    const view = mapStructure({
      metadata: {},
      structure: {},
      statistics: {},
      quality: {},
    })!;
    expect(view.hasContent).toBe(false);
  });

  it("prefers journal over empty venue for display mapping", () => {
    const view = mapStructure({
      metadata: { venue: "Conference X", journal: null },
      structure: {},
      statistics: {},
      quality: {},
    })!;
    expect(view.venue).toBe("Conference X");
    expect(view.journal).toBeUndefined();
  });
});

describe("formatQualityScore", () => {
  it("formats 0–1 scores as percent", () => {
    expect(formatQualityScore(0.85)).toBe("85%");
  });
});
