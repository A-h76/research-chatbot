import { describe, expect, it } from "vitest";
import { extractToc, slugifyHeading } from "./toc";

describe("slugifyHeading", () => {
  it("normalises punctuation and spaces", () => {
    expect(slugifyHeading("1. Global conventions (frozen)")).toBe(
      "1-global-conventions-frozen",
    );
  });
});

describe("extractToc", () => {
  it("collects h2/h3 with unique ids", () => {
    const md = `
# Title
## One
### Nested
## One
## Two
`;
    expect(extractToc(md)).toEqual([
      { id: "one", text: "One", level: 2 },
      { id: "nested", text: "Nested", level: 3 },
      { id: "one-1", text: "One", level: 2 },
      { id: "two", text: "Two", level: 2 },
    ]);
  });
});
