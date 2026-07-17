export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(url: string, opts: RequestInit = {}): Promise<T> {
  const isForm = opts.body instanceof FormData;
  const res = await fetch(url, {
    ...opts,
    headers: isForm ? opts.headers : { "Content-Type": "application/json", ...(opts.headers || {}) },
  });
  if (res.status === 401) {
    window.location.href = "/login";
    throw new ApiError("not_authenticated", 401);
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(body.detail || body.error || "request_failed", res.status);
  }
  return body as T;
}

export const api = {
  get: <T>(url: string) => request<T>(url),
  post: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: "PATCH", body: JSON.stringify(body ?? {}) }),
  delete: <T>(url: string) => request<T>(url, { method: "DELETE" }),
  postForm: <T>(url: string, form: FormData) => request<T>(url, { method: "POST", body: form }),
};
