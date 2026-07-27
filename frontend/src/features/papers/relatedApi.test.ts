import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchRelated, importRelatedPaper } from "./relatedApi";

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

describe("importRelatedPaper", () => {
  it("POSTs metadata stub to /api/discover/import with import_source=related", async () => {
    const fetchMock = mockFetchOnce(201, {
      already_exists: false,
      file: { id: 9, title: "Rel" },
    });
    const paper = {
      paper_id: "abc",
      doi: "10.1/x",
      title: "Rel",
      authors: "A",
      year: 2024,
      venue: "",
      abstract: "",
      citation_count: 0,
      open_access_url: "",
      source: "s2",
    };

    const result = await importRelatedPaper(paper, 3);

    expect(result.file.id).toBe(9);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/discover/import",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
    const body = JSON.parse(String((fetchMock.mock.calls[0][1] as RequestInit).body));
    expect(body.import_source).toBe("related");
    expect(body.openalex_id).toBe("s2:abc");
    expect(body.project_id).toBe(3);
  });
});
