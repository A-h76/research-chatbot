/** Semantic Scholar related papers — thin fetch wrapper for PaperRelatedTab. */

import type { UserFile } from "@/types/api";

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

export interface RelatedImportResult {
  already_exists: boolean;
  file: UserFile;
}

export async function fetchRelated(fileId: number): Promise<RelatedBundle> {
  const res = await fetch(`/api/files/${fileId}/related`, { credentials: "include" });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { message?: string; error?: string };
    throw new Error(body.message || body.error || "unavailable");
  }
  return res.json();
}

/** Metadata-only library stub via the shared Discover import pipeline. */
export async function importRelatedPaper(
  paper: S2Paper,
  projectId: number | null,
): Promise<RelatedImportResult> {
  const res = await fetch("/api/discover/import", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      doi: paper.doi,
      title: paper.title,
      authors: paper.authors,
      year: paper.year,
      venue: paper.venue,
      abstract: paper.abstract,
      open_access_url: paper.open_access_url,
      openalex_id: paper.paper_id ? `s2:${paper.paper_id}` : "",
      project_id: projectId,
      import_source: "related",
    }),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { message?: string; error?: string };
    throw new Error(body.message || body.error || "import_failed");
  }
  return res.json();
}
