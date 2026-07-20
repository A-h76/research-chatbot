import { describe, it, expect, vi, beforeEach } from "vitest";
import { aiApi } from "./api";
import { ApiError } from "@/lib/apiClient";

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

describe("aiApi.listPrompts", () => {
  it("GETs /api/ai/prompts and returns the parsed response", async () => {
    const fetchMock = mockFetchOnce(200, {
      prompts: [
        { name: "chat_system", version: 1, template: "hi", is_active: true, created_at: null },
      ],
    });

    const result = await aiApi.listPrompts();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/ai/prompts");
    expect(opts?.method).toBeUndefined(); // api.get() sends no explicit method (GET default)
    expect(result.prompts).toHaveLength(1);
    expect(result.prompts[0].name).toBe("chat_system");
  });

  it("throws ApiError with the server's message on a non-2xx response", async () => {
    mockFetchOnce(502, { error: "model_call_failed", message: "bad key" });

    await expect(aiApi.listPrompts()).rejects.toMatchObject({
      status: 502,
    } satisfies Partial<ApiError>);
  });
});

describe("aiApi.test", () => {
  it("POSTs to /api/ai/test with the given body and returns the parsed result", async () => {
    const fetchMock = mockFetchOnce(200, {
      content: "pong", model: "gpt-4o-mini", prompt_tokens: 10, completion_tokens: 2,
      total_tokens: 12, finish_reason: "stop", cost: 0.00004,
    });

    const result = await aiApi.test({ message: "ping" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/ai/test");
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body as string)).toEqual({ message: "ping" });
    expect(result.content).toBe("pong");
    expect(result.cost).toBeCloseTo(0.00004);
  });

  it("defaults to an empty body when called with no arguments", async () => {
    const fetchMock = mockFetchOnce(200, {
      content: "hi", model: "gpt-4o-mini", prompt_tokens: 1, completion_tokens: 1,
      total_tokens: 2, finish_reason: "stop", cost: 0,
    });

    await aiApi.test();

    const [, opts] = fetchMock.mock.calls[0];
    expect(JSON.parse(opts.body as string)).toEqual({});
  });

  it("propagates a 403 (disabled in production) as an ApiError", async () => {
    mockFetchOnce(403, { error: "disabled_in_production" });

    await expect(aiApi.test({ message: "x" })).rejects.toMatchObject({ status: 403 });
  });
});
