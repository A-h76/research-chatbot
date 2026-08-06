import { describe, expect, it } from "vitest";
import { projectResearchUrl } from "./projectResearchNavigation";

describe("projectResearchUrl", () => {
  it("builds research tab links", () => {
    expect(projectResearchUrl(5)).toBe("/projects/5?tab=research");
    expect(projectResearchUrl(5, { preset: "evidence" })).toBe(
      "/projects/5?tab=research&preset=evidence",
    );
    expect(projectResearchUrl(5, { query: "What gaps remain?" })).toBe(
      "/projects/5?tab=research&query=What+gaps+remain%3F",
    );
  });
});
