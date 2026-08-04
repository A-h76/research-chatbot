import { describe, expect, it } from "vitest";
import {
  allowedReasoningEfforts,
  isProReasoningModel,
  normalizeReasoningEffort,
  supportsReasoningEffort,
  supportsTemperature,
} from "./modelCapabilities";

describe("modelCapabilities", () => {
  it("hides temperature on gpt-5 / gpt-5.5 family (API rejects it)", () => {
    expect(supportsTemperature("gpt-5.5")).toBe(false);
    expect(supportsTemperature("gpt-5-mini")).toBe(false);
    expect(supportsTemperature("gpt-5.5-pro")).toBe(false);
    expect(supportsTemperature("o3-mini")).toBe(false);
  });

  it("allows temperature on classic chat models", () => {
    expect(supportsTemperature("gpt-4o")).toBe(true);
    expect(supportsTemperature("gpt-4.1")).toBe(true);
  });

  it("exposes reasoning effort for gpt-5 family", () => {
    expect(supportsReasoningEffort("gpt-5.5")).toBe(true);
    expect(supportsReasoningEffort("gpt-5-mini")).toBe(true);
    expect(supportsReasoningEffort("gpt-4o")).toBe(false);
  });

  it("Pro models reject low reasoning effort", () => {
    expect(isProReasoningModel("gpt-5.5-pro")).toBe(true);
    expect(allowedReasoningEfforts("gpt-5.5-pro")).toEqual(["medium", "high"]);
    expect(normalizeReasoningEffort("gpt-5.5-pro", "low")).toBe("medium");
    expect(normalizeReasoningEffort("gpt-5.5", "low")).toBe("low");
  });
});
