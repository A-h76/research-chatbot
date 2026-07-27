/** Semantic Scholar related papers — thin fetch wrapper for PaperRelatedTab. */

export interface S2Paper {
  paper_id: string;
  doi: string;
  title: string;
  authors: string;
  year: number | null;
  venue: string;
  abstract: string;
  citation_count: number;
  open_access_url: string;
  source: string;
}

export interface RelatedBundle {
  related: S2Paper[];
  citing: S2Paper[];
  recommended: S2Paper[];
  cached_at: string;
  provider_version: string;
}

export async function fetchRelated(fileId: number): Promise<RelatedBundle> {
  const res = await fetch(`/api/files/${fileId}/related`, { credentials: "include" });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { message?: string };
    throw new Error(body.message || "unavailable");
  }
  return res.json();
}
