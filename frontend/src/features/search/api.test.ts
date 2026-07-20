import { describe, it, expect, vi, beforeEach } from "vitest";
import { ragApi } from "./api";

function mockFetch(responses: Record<string, { status: number; body: unknown }>) {
  const fetchMock = vi.fn((url: string, _opts?: RequestInit) => {
    const r = responses[url];
    if (!r) throw new Error(`unexpected fetch to ${url}`);
    return Promise.resolve({
      status: r.status,
      ok: r.status >= 200 && r.status < 300,
      json: () => Promise.resolve(r.body),
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe("ragApi.ask", () => {
  it("bridges a JWT and POSTs the query to /api/rag", async () => {
    const fetchMock = mockFetch({
      "/api/auth/jwt": { status: 200, body: { access_token: "tokrag", refresh_token: "r" } },
      "/api/rag": {
        status: 200,
        body: {
          answer: "It's about X.",
          model: "gpt-4o-mini",
          sources: [{ document_id: 1, chunk_id: 2, title: "Paper", score: 0.8, page: 3, section: null }],
        },
      },
    });

    const result = await ragApi.ask({ query: "what is this about", project_id: null });

    const call = fetchMock.mock.calls.find((c) => c[0] === "/api/rag")!;
    expect((call[1] as RequestInit).method).toBe("POST");
    expect((call[1] as RequestInit).headers).toMatchObject({ Authorization: "Bearer tokrag" });
    expect(JSON.parse((call[1] as RequestInit).body as string)).toEqual({
      query: "what is this about",
      project_id: null,
    });
    expect(result.answer).toBe("It's about X.");
    expect(result.sources).toHaveLength(1);
  });

  it("surfaces the no-results message when answer is null", async () => {
    mockFetch({
      "/api/auth/jwt": { status: 200, body: { access_token: "tok", refresh_token: "r" } },
      "/api/rag": {
        status: 200,
        body: { answer: null, sources: [], message: "No relevant documents found for this query." },
      },
    });

    const result = await ragApi.ask({ query: "obscure query" });

    expect(result.answer).toBeNull();
    expect(result.message).toBe("No relevant documents found for this query.");
  });
});
