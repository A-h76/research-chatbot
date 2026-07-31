import { describe, expect, it } from "vitest";
import {
  displayHeadingLabel,
  isSectionBodyHeading,
  isSpacedLetterHeading,
  parseSectionBody,
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
      { kind: "paragraph", text: "Liver\nKupffer cells (KCs)" },
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
});
