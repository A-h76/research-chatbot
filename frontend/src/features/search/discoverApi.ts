/** OpenAlex Discover — thin fetch wrapper used by SearchPage. */

import { ApiError } from "@/lib/apiClient";

export interface OpenAlexWork {
  id: string;
  doi: string;
  title: string;
  authors: string;
  year: number | null;
  venue: string;
  abstract: string;
  citation_count: number;
  open_access_url: string;
  concepts: string[];
  source: string;
}

export interface DiscoverResponse {
  results: OpenAlexWork[];
  page: number;
}

export async function discoverWorks(
  query: string,
  page: number,
  perPage = 15,
): Promise<DiscoverResponse> {
  const params = new URLSearchParams({
    q: query,
    page: String(page),
    per_page: String(perPage),
  });
  const res = await fetch(`/api/discover?${params}`, { credentials: "include" });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    const code = typeof body.error === "string" ? body.error : "discover_unavailable";
    throw new ApiError(String(body.detail || body.error || "discover_unavailable"), res.status, {
      code,
      body,
    });
  }
  return res.json();
}
