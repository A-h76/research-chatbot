/** Discover (OpenAlex + PubMed + arXiv + Europe PMC + ORCID) — thin fetch wrappers. */

import { ApiError } from "@/lib/apiClient";

export type DiscoverProvider =
  | "openalex"
  | "pubmed"
  | "arxiv"
  | "europe_pmc"
  | "orcid";

export interface DiscoverWork {
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
  pmid?: string;
  pmcid?: string;
  arxiv_id?: string;
  europe_pmc_id?: string;
  orcid_id?: string;
  put_code?: string;
  is_open_access?: boolean;
  primary_category?: string;
}

/** @deprecated Prefer DiscoverWork — kept for existing imports */
export type OpenAlexWork = DiscoverWork;

export interface DiscoverResponse {
  results: DiscoverWork[];
  page: number;
  provider?: DiscoverProvider;
}

export interface DiscoverImportResult {
  already_exists: boolean;
  file: { id: number };
  provider?: string;
  pdf_attached?: boolean;
  analysis_queued?: boolean;
  pdf_error?: string | null;
  fulltext?: {
    outcome?: string | null;
    user_reason?: string | null;
    full_text_source?: string;
    attempts?: unknown[];
    last_attempt_at?: string | null;
    found?: boolean;
  } | null;
}

export async function discoverWorks(
  query: string,
  page: number,
  perPage = 15,
  provider: DiscoverProvider = "openalex",
): Promise<DiscoverResponse> {
  const params = new URLSearchParams({
    q: query,
    page: String(page),
    per_page: String(perPage),
    provider,
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

export async function importDiscoverWork(
  work: DiscoverWork,
  projectId: number | null,
  provider: DiscoverProvider = "openalex",
): Promise<DiscoverImportResult> {
  const body: Record<string, unknown> = {
    provider,
    doi: work.doi,
    title: work.title,
    authors: work.authors,
    year: work.year,
    venue: work.venue,
    abstract: work.abstract,
    open_access_url: work.open_access_url,
    project_id: projectId,
  };
  if (provider === "pubmed") {
    body.pmid = work.pmid || work.id;
    body.pmcid = work.pmcid || "";
    body.id = work.pmid || work.id;
  } else if (provider === "arxiv") {
    body.arxiv_id = work.arxiv_id || work.id;
    body.id = work.arxiv_id || work.id;
  } else if (provider === "europe_pmc") {
    body.pmcid = work.pmcid || "";
    body.pmid = work.pmid || "";
    body.europe_pmc_id = work.europe_pmc_id || work.id;
    body.id = work.europe_pmc_id || work.pmcid || work.pmid || work.id;
  } else if (provider === "orcid") {
    body.orcid_id = work.orcid_id || "";
    body.put_code = work.put_code || "";
    body.pmid = work.pmid || "";
    body.pmcid = work.pmcid || "";
    body.arxiv_id = work.arxiv_id || "";
    body.id = work.id;
  } else {
    body.openalex_id = work.id;
  }
  const res = await fetch("/api/discover/import", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.message || errBody.error || "import_failed");
  }
  return res.json();
}
