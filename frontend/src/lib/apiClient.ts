export class ApiError extends Error {
  status: number;
  /** Machine code from JSON `error` when present (e.g. feature_disabled). */
  code?: string;
  /** Raw JSON body for structured fields (quota, detail, …). */
  body?: Record<string, unknown>;
  /** Parsed entitlement payload when BE attached `quota`. */
  quota?: import("@/features/settings/quotaMessaging").QuotaPayload | null;

  constructor(
    message: string,
    status: number,
    opts?: {
      code?: string;
      body?: Record<string, unknown>;
      quota?: import("@/features/settings/quotaMessaging").QuotaPayload | null;
    },
  ) {
    super(message);
    this.status = status;
    this.code = opts?.code;
    this.body = opts?.body;
    this.quota = opts?.quota ?? null;
  }
}

/** Prevents a stampede of 401s from opening the modal repeatedly. */
let sessionExpiredDispatched = false;

/** D9 / M11 — notify shell instead of hard-redirecting mid-flight. */
function handleUnauthorized() {
  if (sessionExpiredDispatched) return;
  sessionExpiredDispatched = true;
  window.dispatchEvent(new CustomEvent("soro:session-expired"));
}

function parseQuota(body: Record<string, unknown>) {
  const q = body.quota;
  if (q && typeof q === "object") {
    return q as import("@/features/settings/quotaMessaging").QuotaPayload;
  }
  const err = String(body.error || "");
  if (
    err === "token_quota_exceeded" ||
    err === "cost_quota_exceeded" ||
    err === "storage_quota_exceeded"
  ) {
    return {
      error: err,
      message: String(body.detail || body.message || "Usage limit reached."),
      label: err.includes("storage") ? "Storage" : "AI usage",
    };
  }
  return null;
}

async function request<T>(url: string, opts: RequestInit = {}): Promise<T> {
  const isForm = opts.body instanceof FormData;
  const res = await fetch(url, {
    ...opts,
    headers: isForm ? opts.headers : { "Content-Type": "application/json", ...(opts.headers || {}) },
  });
  if (res.status === 401) {
    handleUnauthorized();
    throw new ApiError("session_expired", 401);
  }
  const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (!res.ok) {
    const code = typeof body.error === "string" ? body.error : undefined;
    const message = String(body.detail || body.error || body.message || "request_failed");
    throw new ApiError(message, res.status, {
      code,
      body,
      quota: parseQuota(body),
    });
  }
  return body as T;
}

export const api = {
  // token is for JWT-only GET routes (e.g. the bulk-upload batch status
  // route) — everything else here rides the session cookie, no token needed.
  get: <T>(url: string, token?: string) =>
    request<T>(url, { headers: token ? { Authorization: `Bearer ${token}` } : undefined }),
  post: <T>(url: string, body?: unknown, token?: string) =>
    request<T>(url, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    }),
  patch: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: "PATCH", body: JSON.stringify(body ?? {}) }),
  delete: <T>(url: string, body?: unknown) =>
    request<T>(url, {
      method: "DELETE",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  // token is for JWT-only routes (e.g. /api/documents/upload) — everything
  // else here rides the session cookie, no token needed.
  postForm: <T>(url: string, form: FormData, token?: string) =>
    request<T>(url, {
      method: "POST",
      body: form,
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    }),
};

// Bridges the existing session cookie into a Bearer token for routes that
// are @jwt_required() only (GET /api/auth/jwt mints/refreshes as needed —
// see server.py). No client-side caching: access tokens are short-lived
// (15 min) and this isn't called often enough to be worth tracking expiry.
export async function getBearerToken(): Promise<string> {
  const { access_token } = await request<{ access_token: string; refresh_token: string }>(
    "/api/auth/jwt"
  );
  return access_token;
}
