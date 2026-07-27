import { describe, it, expect, vi, beforeEach } from "vitest";
import { discoverWorks } from "./discoverApi";

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

describe("discoverWorks", () => {
  it("GETs /api/discover with query + pagination and returns results", async () => {
    const fetchMock = mockFetchOnce(200, {
      results: [
        {
          id: "W1",
          doi: "10.1/x",
          title: "OpenAlex Paper",
          authors: "Ada",
          year: 2024,
          venue: "Nature",
          abstract: "abs",
          citation_count: 3,
          open_access_url: "",
          concepts: ["AI"],
          source: "openalex",
        },
      ],
      page: 1,
    });

    const result = await discoverWorks("transformers", 1);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/api/discover?");
    expect(String(url)).toContain("q=transformers");
    expect(String(url)).toContain("page=1");
    expect(String(url)).toContain("per_page=15");
    expect(opts).toMatchObject({ credentials: "include" });
    expect(result.results[0]?.title).toBe("OpenAlex Paper");
    expect(result.page).toBe(1);
  });

  it("throws discover_unavailable on non-2xx so the UI can show a soft failure", async () => {
    mockFetchOnce(503, { error: "down" });
    await expect(discoverWorks("crp", 1)).rejects.toThrow("discover_unavailable");
  });
});
