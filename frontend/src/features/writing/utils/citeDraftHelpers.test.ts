/**
 * @vitest-environment node
 */
import { describe, expect, it } from "vitest";
import {
  insertAtCaret,
  removeEvidenceMarker,
  replaceSelection,
  selectedEvidenceMarkerId,
} from "./citeDraftHelpers";

describe("citeDraftHelpers", () => {
  it("inserts at caret with spacing", () => {
    const r = insertAtCaret("Hello world", "[#1]", 5, 5);
    expect(r.content).toBe("Hello [#1] world");
  });

  it("replaces selection", () => {
    const r = replaceSelection("See [#2] here", "[#9]", 4, 8);
    expect(r.content).toContain("[#9]");
    expect(r.content).not.toContain("[#2]");
  });

  it("detects selected evidence marker", () => {
    expect(selectedEvidenceMarkerId("x [#3] y", 2, 6)).toBe(3);
    expect(selectedEvidenceMarkerId("x [#3] y", 3, 3)).toBe(3);
  });

  it("removes all markers for an id", () => {
    const r = removeEvidenceMarker("A [#1]. B [#1].", 1);
    expect(r.removed).toBe(2);
    expect(r.content).not.toContain("[#1]");
  });
});
