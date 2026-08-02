/** User-facing quota / entitlement messaging (#13). */

export type QuotaPayload = {
  error?: string | null;
  operation?: string;
  label?: string;
  message?: string;
  used?: number;
  limit?: number;
  remaining?: number;
  reset_at?: string | null;
  plan?: string;
  warning?: boolean;
  percent?: number;
  upgrade_hint?: string | null;
  learn_more?: string;
};

export function formatQuotaMessage(q: QuotaPayload | null | undefined, fallback?: string): string {
  if (!q) return fallback || "Usage limit reached.";
  if (q.message) return q.message;
  const label = q.label || "This feature";
  const used = q.used != null && q.limit != null ? `\n\nUsed: ${q.used.toLocaleString()} / ${q.limit.toLocaleString()}` : "";
  return `${label}\n\nYou've reached your monthly limit.${used}`;
}

export function quotaFromApiError(body: unknown): QuotaPayload | null {
  if (!body || typeof body !== "object") return null;
  const b = body as Record<string, unknown>;
  if (b.quota && typeof b.quota === "object") return b.quota as QuotaPayload;
  const err = String(b.error || "");
  if (
    err === "token_quota_exceeded" ||
    err === "cost_quota_exceeded" ||
    err === "storage_quota_exceeded"
  ) {
    return {
      error: err,
      message: String(b.detail || b.message || "Usage limit reached."),
      label: err.includes("storage") ? "Storage" : "AI usage",
    };
  }
  return null;
}
