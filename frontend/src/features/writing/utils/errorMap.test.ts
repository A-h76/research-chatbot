import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/apiClient";
import { mapWritingError } from "./errorMap";

describe("mapWritingError", () => {
  it("maps conflict and auth statuses", () => {
    expect(mapWritingError(new ApiError("x", 409))).toMatch(/conflict/i);
    expect(mapWritingError(new ApiError("x", 403))).toMatch(/access/i);
    expect(mapWritingError(new ApiError("x", 404))).toMatch(/not found/i);
  });

  it("falls back for unknown errors", () => {
    expect(mapWritingError(new Error("boom"))).toBe("Unexpected writing error.");
  });
});
