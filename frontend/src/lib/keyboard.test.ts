/** @vitest-environment jsdom */
import { describe, expect, it } from "vitest";
import { isTypingTarget } from "./keyboard";

describe("isTypingTarget", () => {
  it("returns false for null / non-elements", () => {
    expect(isTypingTarget(null)).toBe(false);
  });

  it("detects input and textarea", () => {
    const input = document.createElement("input");
    const ta = document.createElement("textarea");
    expect(isTypingTarget(input)).toBe(true);
    expect(isTypingTarget(ta)).toBe(true);
  });

  it("detects contenteditable", () => {
    const div = document.createElement("div");
    div.setAttribute("contenteditable", "true");
    expect(isTypingTarget(div)).toBe(true);
  });

  it("allows shortcuts on buttons", () => {
    const btn = document.createElement("button");
    expect(isTypingTarget(btn)).toBe(false);
  });
});
