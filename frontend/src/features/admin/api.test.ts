import { describe, it, expect, vi, beforeEach } from "vitest";
import { adminOpsApi } from "./api";

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

describe("adminOpsApi", () => {
  it("GETs ops settings", async () => {
    const fetchMock = mockFetchOnce(200, {
      ai_disabled: false,
      daily: { spend_usd: 0.1, budget_usd: 10 },
    });
    const snap = await adminOpsApi.getSettings();
    expect(String(fetchMock.mock.calls[0]![0])).toContain("/api/admin/ops/settings");
    expect(snap.ai_disabled).toBe(false);
  });

  it("PATCHes kill switch", async () => {
    const fetchMock = mockFetchOnce(200, { ai_disabled: true, daily: {} });
    await adminOpsApi.patchSettings({ ai_disabled: true });
    const [url, opts] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/api/admin/ops/settings");
    expect(opts).toMatchObject({ method: "PATCH" });
    expect(JSON.parse(String(opts?.body))).toEqual({ ai_disabled: true });
  });

  it("POSTs invite", async () => {
    const fetchMock = mockFetchOnce(201, {
      ok: true,
      email: "a@b.com",
      token: "tok",
      email_sent: false,
    });
    const res = await adminOpsApi.createInvite("a@b.com");
    expect(String(fetchMock.mock.calls[0]![0])).toContain("/api/admin/ops/invites");
    expect(res.token).toBe("tok");
  });

  it("GETs beta metrics with days", async () => {
    const fetchMock = mockFetchOnce(200, {
      period_days: 7,
      since: "2026-01-01T00:00:00Z",
      counts: {
        new_users: 1,
        returning_users: 0,
        new_projects: 0,
        papers_analysed: 0,
        research_runs: 0,
        memories_promoted: 0,
      },
      funnel_all_time: {
        users_with_projects: 0,
        users_2plus_analysed_papers: 0,
        users_with_research_run: 0,
      },
      targets: { activation: "x", retention: "y" },
    });
    await adminOpsApi.betaMetrics(7);
    expect(String(fetchMock.mock.calls[0]![0])).toContain("/api/admin/ops/beta-metrics?days=7");
  });

  it("GETs security events", async () => {
    const fetchMock = mockFetchOnce(200, { items: [] });
    await adminOpsApi.securityEvents(50, "login");
    const url = String(fetchMock.mock.calls[0]![0]);
    expect(url).toContain("/api/admin/ops/security-events?");
    expect(url).toContain("limit=50");
    expect(url).toContain("event=login");
  });
});
