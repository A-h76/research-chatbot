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
    expect(String(url)).toContain("provider=openalex");
    expect(opts).toMatchObject({ credentials: "include" });
    expect(result.results[0]?.title).toBe("OpenAlex Paper");
    expect(result.page).toBe(1);
  });

  it("passes provider=pubmed when requested", async () => {
    const fetchMock = mockFetchOnce(200, { results: [], page: 1, provider: "pubmed" });
    await discoverWorks("crp", 1, 15, "pubmed");
    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("provider=pubmed");
  });

  it("passes provider=arxiv when requested", async () => {
    const fetchMock = mockFetchOnce(200, { results: [], page: 1, provider: "arxiv" });
    await discoverWorks("transformers", 1, 15, "arxiv");
    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("provider=arxiv");
  });

  it("passes provider=europe_pmc when requested", async () => {
    const fetchMock = mockFetchOnce(200, { results: [], page: 1, provider: "europe_pmc" });
    await discoverWorks("crp", 1, 15, "europe_pmc");
    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("provider=europe_pmc");
  });

  it("passes provider=orcid when requested", async () => {
    const fetchMock = mockFetchOnce(200, { results: [], page: 1, provider: "orcid" });
    await discoverWorks("0000-0002-1825-0097", 1, 15, "orcid");
    const [url] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("provider=orcid");
  });

  it("throws ApiError on non-2xx so the UI can show a soft failure", async () => {
    mockFetchOnce(503, { error: "feature_disabled" });
    await expect(discoverWorks("crp", 1)).rejects.toMatchObject({
      message: "feature_disabled",
      code: "feature_disabled",
      status: 503,
    });
  });
});
