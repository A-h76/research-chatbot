import { describe, expect, it } from "vitest";
import {
  applyHeadingToLine,
  applyTextColor,
  detectHeadingLevel,
  toggleInlineMark,
} from "./writingFormatHelpers";

describe("writingFormatHelpers", () => {
  it("toggles bold around selection", () => {
    const r = toggleInlineMark("hello world", 0, 5, "**");
    expect(r.content).toBe("**hello** world");
  });

  it("applies heading to line", () => {
    const r = applyHeadingToLine("Deep Learning Approaches\nmore", 0, 0, "h2");
    expect(r.content.startsWith("## Deep Learning Approaches")).toBe(true);
    expect(detectHeadingLevel(r.content, 3)).toBe("h2");
  });

  it("wraps color span", () => {
    const r = applyTextColor("hello", 0, 5, "#0f6e6a");
    expect(r.content).toContain('style="color:#0f6e6a"');
    expect(r.content).toContain("hello");
  });
});
