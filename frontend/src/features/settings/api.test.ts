import { describe, it, expect, vi, beforeEach } from "vitest";
import { settingsApi } from "./api";

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

describe("settingsApi.deleteAccount", () => {
  it("DELETEs /api/account with step-up body", async () => {
    const fetchMock = mockFetchOnce(200, { ok: true });
    await settingsApi.deleteAccount({ confirm: "DELETE", password: "secret" });
    const [url, opts] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/api/account");
    expect(opts).toMatchObject({ method: "DELETE" });
    expect(JSON.parse(String(opts?.body))).toEqual({
      confirm: "DELETE",
      password: "secret",
    });
  });
});
