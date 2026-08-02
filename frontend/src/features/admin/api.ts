import { api } from "@/lib/apiClient";

export type OpsSettings = {
  ai_disabled: boolean;
  daily: {
    date?: string;
    spend_usd?: number;
    budget_usd?: number;
    pct?: number;
    paused?: boolean;
    warn_80?: boolean;
    warn_95?: boolean;
  };
};

export type InviteItem = {
  id: number;
  email: string;
  created_at: string | null;
  expires_at: string | null;
  used_at: string | null;
  expired: boolean;
};

export type BetaMetrics = {
  period_days: number;
  since: string;
  counts: {
    new_users: number;
    returning_users: number;
    new_projects: number;
    papers_analysed: number;
    research_runs: number;
    memories_promoted: number;
  };
  funnel_all_time: {
    users_with_projects: number;
    users_2plus_analysed_papers: number;
    users_with_research_run: number;
  };
  targets: {
    activation: string;
    retention: string;
  };
};

export type SecurityEventItem = {
  id: number;
  event: string;
  user_id: number | null;
  detail: Record<string, unknown>;
  ip: string;
  created_at: string | null;
};

export type FeatureFlagItem = {
  flag_name: string;
  enabled: boolean;
  user_id: number | null;
  rollout_pct: number | null;
  updated_at: string | null;
  source?: string;
  description?: string | null;
};

export const adminOpsApi = {
  getSettings: () => api.get<OpsSettings>("/api/admin/ops/settings"),
  patchSettings: (body: { ai_disabled?: boolean; daily_ai_budget_usd?: number }) =>
    api.patch<OpsSettings>("/api/admin/ops/settings", body),

  listInvites: (includeUsed = false) =>
    api.get<{ items: InviteItem[] }>(
      `/api/admin/ops/invites${includeUsed ? "?include_used=1" : ""}`,
    ),
  createInvite: (email: string, sendEmail = true) =>
    api.post<{ ok: boolean; email: string; token: string; email_sent: boolean }>(
      "/api/admin/ops/invites",
      { email, send_email: sendEmail },
    ),

  betaMetrics: (days = 7) =>
    api.get<BetaMetrics>(`/api/admin/ops/beta-metrics?days=${days}`),

  securityEvents: (limit = 100, event?: string) => {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (event) qs.set("event", event);
    return api.get<{ items: SecurityEventItem[] }>(
      `/api/admin/ops/security-events?${qs.toString()}`,
    );
  },

  listFeatureFlags: () =>
    api.get<{ flags: FeatureFlagItem[] }>("/api/admin/ops/feature-flags"),
  setFeatureFlag: (
    flagName: string,
    body: { enabled: boolean; rollout_pct?: number | null; user_id?: number | null },
  ) =>
    api.patch<{ ok: boolean; flag: FeatureFlagItem }>(
      `/api/admin/ops/feature-flags/${encodeURIComponent(flagName)}`,
      body,
    ),

  getUserQuota: (userId: number) =>
    api.get<QuotaUsageSnapshot>(`/api/admin/ops/quotas/${userId}`),
  patchUserQuota: (
    userId: number,
    body: {
      monthly_token_limit?: number;
      monthly_cost_limit?: number;
      storage_limit_bytes?: number;
      plan?: string;
    },
  ) => api.patch<{ ok: boolean; usage: QuotaUsageSnapshot }>(`/api/admin/ops/quotas/${userId}`, body),
  resetUserQuota: (userId: number) =>
    api.post<{ ok: boolean; usage: QuotaUsageSnapshot }>(
      `/api/admin/ops/quotas/${userId}/reset`,
    ),
  getQuotasDisabled: () =>
    api.get<{ quotas_disabled: boolean }>("/api/admin/ops/quotas/disabled"),
  setQuotasDisabled: (disabled: boolean) =>
    api.post<{ ok: boolean; quotas_disabled: boolean }>("/api/admin/ops/quotas/disabled", {
      disabled,
    }),
  quotaAnalytics: (days = 30) =>
    api.get<QuotaAnalytics>(`/api/admin/ops/quotas/analytics?days=${days}`),

  workerHealth: async () => {
    const res = await fetch("/api/worker/health", { credentials: "include" });
    const body = (await res.json().catch(() => ({}))) as WorkerHealth;
    // 503 when down still carries a useful status body.
    return {
      status: body.status || (res.ok ? "ok" : "unknown"),
      age_seconds: body.age_seconds ?? null,
      detail: body.detail,
    };
  },
};

export type QuotaUsageSnapshot = {
  plan?: string;
  quotas_disabled?: boolean;
  tokens?: {
    used?: number;
    limit?: number;
    remaining?: number;
    percent?: number;
    reset_at?: string | null;
    warning?: boolean;
  };
  token_used?: number;
  token_limit?: number;
  storage_used_bytes?: number;
  storage_limit_bytes?: number;
  [key: string]: unknown;
};

export type QuotaAnalytics = {
  days: number;
  total_units: number;
  by_operation: Array<{ operation: string; units: number }>;
  by_user: Array<{ user_id: number; units: number }>;
};

export type WorkerHealth = {
  status: "ok" | "down" | "unknown" | string;
  age_seconds?: number | null;
  detail?: string;
};
