import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/apiClient";
import {
  formatApiFailure,
  isFeatureDisabledError,
  quotaFromUnknown,
} from "./apiErrors";

describe("formatApiFailure", () => {
  it("maps feature_disabled", () => {
    expect(
      formatApiFailure(new ApiError("feature_disabled", 503, { code: "feature_disabled" })),
    ).toBe("This feature is temporarily off.");
    expect(isFeatureDisabledError(new Error("feature_disabled"))).toBe(true);
  });

  it("prefers quota message", () => {
    const err = new ApiError("token_quota_exceeded", 429, {
      code: "token_quota_exceeded",
      quota: {
        message: "You've reached your Writing Intelligence limit.",
        used: 100,
        limit: 100,
      },
    });
    expect(formatApiFailure(err)).toContain("Writing Intelligence");
    expect(quotaFromUnknown(err)?.used).toBe(100);
  });
});
