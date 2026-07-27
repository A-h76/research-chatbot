import { describe, it, expect } from "vitest";
import { parsePaperTab, PAPER_TABS, PAPER_TAB_LABELS } from "./tabs";

describe("parsePaperTab", () => {
  it("defaults to overview", () => {
    expect(parsePaperTab(null)).toBe("overview");
    expect(parsePaperTab(undefined)).toBe("overview");
    expect(parsePaperTab("nope")).toBe("overview");
  });

  it("accepts every workspace tab id", () => {
    for (const tab of PAPER_TABS) {
      expect(parsePaperTab(tab)).toBe(tab);
      expect(PAPER_TAB_LABELS[tab]).toBeTruthy();
    }
  });
});
