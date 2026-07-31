import { describe, expect, it } from "vitest";
import {
  looksLikeBibliographyHeading,
  parseCitationPreview,
  splitReferenceLines,
} from "./citationPreview";
import { mapStructure } from "./structure";

describe("citationPreview", () => {
  it("parses vancouver-ish author / title / journal / year", () => {
    const c = parseCitationPreview(
      "1. Guilliams M, Scott CL. Liver macrophages in health and disease. Immunity. 2016;45:1-10.",
      0,
    );
    expect(c.authorsLine).toMatch(/Guilliams/);
    expect(c.titleLine).toMatch(/Liver macrophages/i);
    expect(c.year).toBe(2016);
    expect(c.parsed).toBe(true);
  });

  it("extracts DOI when present", () => {
    const c = parseCitationPreview(
      "Smith A. A paper. Nature. 2020. doi:10.1038/s41586-020-0000",
      1,
    );
    expect(c.doi).toBe("10.1038/s41586-020-0000");
  });

  it("splits numbered reference blobs", () => {
    const lines = splitReferenceLines(
      "1. First citation here about cells.\n2. Second citation about liver.\n3. Third one.",
    );
    expect(lines).toHaveLength(3);
  });

  it("detects numbered bibliography headings", () => {
    expect(
      looksLikeBibliographyHeading(
        "1. Guilliams M, Scott CL. Liver macrophages in health and disease. Immunity.",
      ),
    ).toBe(true);
    expect(looksLikeBibliographyHeading("1. Introduction", "Long body…".repeat(20))).toBe(false);
  });
});

describe("mapStructure references", () => {
  it("prefers structure.references and keeps them out of the outline", () => {
    const view = mapStructure({
      metadata: {},
      structure: {
        heading_order: ["Introduction", "References"],
        raw_headings: {
          Introduction: "Intro body",
          References: "1. A.\n2. B.",
        },
        section_types: {
          Introduction: "introduction",
          References: "references",
        },
        references: [
          "1. Guilliams M, Scott CL. Liver macrophages. Immunity. 2016.",
          "2. Liu S. Another paper. Nature. 2023.",
        ],
      },
      statistics: { reference_count: 2 },
      quality: {},
    })!;

    expect(view.references).toHaveLength(2);
    expect(view.sections.map((s) => s.heading)).toEqual(["Introduction"]);
    expect(view.referenceCount).toBe(2);
  });

  it("steals false Structure headings that are really citations", () => {
    const view = mapStructure({
      metadata: {},
      structure: {
        heading_order: [
          "Introduction",
          "1. Guilliams M, Scott CL. Liver macrophages in health and disease. Immunity.",
          "2. Liu S, Cheng C. Another long citation about Kupffer cells. Nature Reviews.",
          "3. Fan X et al. Third citation with enough length. Nat Commun. 2023.",
        ],
        raw_headings: {
          Introduction: "Body",
          "1. Guilliams M, Scott CL. Liver macrophages in health and disease. Immunity.": "",
          "2. Liu S, Cheng C. Another long citation about Kupffer cells. Nature Reviews.": "",
          "3. Fan X et al. Third citation with enough length. Nat Commun. 2023.": "",
        },
        section_types: {
          Introduction: "introduction",
          "1. Guilliams M, Scott CL. Liver macrophages in health and disease. Immunity.": "other",
          "2. Liu S, Cheng C. Another long citation about Kupffer cells. Nature Reviews.": "other",
          "3. Fan X et al. Third citation with enough length. Nat Commun. 2023.": "other",
        },
      },
      statistics: {},
      quality: {},
    })!;

    expect(view.sections.map((s) => s.heading)).toEqual(["Introduction"]);
    expect(view.references.length).toBe(3);
  });
});
