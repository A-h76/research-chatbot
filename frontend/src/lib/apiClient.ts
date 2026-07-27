export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
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
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(body.detail || body.error || "request_failed", res.status);
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
  delete: <T>(url: string) => request<T>(url, { method: "DELETE" }),
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
