import { describe, expect, it } from "vitest";
import {
  displayHeadingLabel,
  isSectionBodyHeading,
  isSpacedLetterHeading,
  parseSectionBody,
  unwrapSoftWrappedLines,
} from "./sectionContent";

describe("sectionContent", () => {
  it("detects spaced PDF abstract headings", () => {
    expect(isSpacedLetterHeading("a b s t r a c t")).toBe(true);
    expect(displayHeadingLabel("a b s t r a c t")).toBe("Abstract");
  });

  it("detects Keywords label", () => {
    expect(isSectionBodyHeading("Keywords:")).toBe(true);
    expect(displayHeadingLabel("Keywords:")).toBe("Keywords");
  });

  it("parses keywords + spaced abstract into bold headings", () => {
    const blocks = parseSectionBody(
      [
        "Keywords:",
        "Liver",
        "Kupffer cells (KCs)",
        "",
        "a b s t r a c t",
        "Kupffer cells play vital roles.",
      ].join("\n"),
    );
    expect(blocks).toEqual([
      { kind: "heading", label: "Keywords" },
      { kind: "paragraph", text: "Liver Kupffer cells (KCs)" },
      { kind: "heading", label: "Abstract" },
      { kind: "paragraph", text: "Kupffer cells play vital roles." },
    ]);
  });

  it("keeps Keywords: inline rest on the heading block", () => {
    const blocks = parseSectionBody("Keywords: liver, inflammation\nMore text.");
    expect(blocks[0]).toEqual({
      kind: "heading",
      label: "Keywords",
      rest: "liver, inflammation",
    });
    expect(blocks[1]).toEqual({ kind: "paragraph", text: "More text." });
  });

  it("reflows soft-wrapped PDF lines into full-width prose", () => {
    const text = unwrapSoftWrappedLines([
      "As the largest parenchymal organ in the human body, the liver accounts",
      "for approximately 2% of body weight, and plays a central role in key",
      "physiological processes such as metabolism, detoxifi",
      "cation, and immune regulation.",
    ]);
    expect(text).toBe(
      "As the largest parenchymal organ in the human body, the liver accounts for approximately 2% of body weight, and plays a central role in key physiological processes such as metabolism, detoxification, and immune regulation.",
    );
  });

  it("dehyphenates PDF line wraps", () => {
    expect(unwrapSoftWrappedLines(["detoxifi-", "cation works"])).toBe("detoxification works");
  });

  it("keeps blank-line paragraph breaks across all sections", () => {
    const blocks = parseSectionBody(
      ["First soft", "wrapped sentence.", "", "Second paragraph", "continues here."].join("\n"),
    );
    expect(blocks).toEqual([
      { kind: "paragraph", text: "First soft wrapped sentence." },
      { kind: "paragraph", text: "Second paragraph continues here." },
    ]);
  });
});
