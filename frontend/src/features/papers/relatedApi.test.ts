import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchRelated } from "./relatedApi";

function mockFetchOnce(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue({
    status,
    ok: status >= 200 && status < 300,
    json: () => Promise.resolve(body),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchRelated", () => {
  it("GETs /api/files/:id/related with session credentials", async () => {
    const bundle = {
      related: [{ paper_id: "r1", doi: "", title: "Ref", authors: "", year: 2020, venue: "", abstract: "", citation_count: 0, open_access_url: "", source: "s2" }],
      citing: [],
      recommended: [],
      cached_at: "2026-07-01T00:00:00Z",
      provider_version: "v1",
    };
    const fetchMock = mockFetchOnce(200, bundle);

    const result = await fetchRelated(42);

    expect(fetchMock).toHaveBeenCalledWith("/api/files/42/related", { credentials: "include" });
    expect(result.related[0]?.title).toBe("Ref");
  });

  it("surfaces server message or 'unavailable' for soft UI failure", async () => {
    mockFetchOnce(502, { message: "unavailable" });
    await expect(fetchRelated(1)).rejects.toThrow("unavailable");
  });
});
