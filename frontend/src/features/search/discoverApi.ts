/** OpenAlex Discover — thin fetch wrapper used by SearchPage. */

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
  if (!res.ok) throw new Error("discover_unavailable");
  return res.json();
}
