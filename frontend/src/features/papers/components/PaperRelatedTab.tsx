/**
 * PaperRelatedTab — Related / Citing / Recommended papers via Semantic Scholar.
 *
 * Fetches from GET /api/files/:id/related.
 * Cache: 7 days server-side; no re-fetch on tab switch until stale.
 * Fails gracefully: shows a neutral "unavailable" message rather than an error.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ExternalLink, BookOpen, Quote, Sparkles, Loader2, AlertCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface S2Paper {
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

interface RelatedBundle {
  related: S2Paper[];
  citing: S2Paper[];
  recommended: S2Paper[];
  cached_at: string;
  provider_version: string;
}

async function fetchRelated(fileId: number): Promise<RelatedBundle> {
  const res = await fetch(`/api/files/${fileId}/related`, { credentials: "include" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || "unavailable");
  }
  return res.json();
}

function PaperCard({ paper }: { paper: S2Paper }) {
  const [expanded, setExpanded] = useState(false);
  const href = paper.doi
    ? `https://doi.org/${paper.doi}`
    : paper.open_access_url || null;

  return (
    <div className="group rounded-xl border border-border bg-card p-4 transition-shadow hover:shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium leading-snug text-foreground line-clamp-2">
            {paper.title || "Untitled"}
          </p>
          {paper.authors && (
            <p className="mt-1 text-xs text-muted-foreground truncate">{paper.authors}</p>
          )}
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            {paper.year && (
              <span className="text-xs text-muted-foreground">{paper.year}</span>
            )}
            {paper.venue && (
              <span className="text-xs text-muted-foreground truncate max-w-[180px]">
                · {paper.venue}
              </span>
            )}
            {paper.citation_count > 0 && (
              <Badge variant="secondary" className="text-xs gap-1 py-0">
                <Quote className="size-3" />
                {paper.citation_count.toLocaleString()}
              </Badge>
            )}
          </div>
        </div>

        {href && (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            title="Open paper"
          >
            <ExternalLink className="size-3.5" />
          </a>
        )}
      </div>

      {paper.abstract && (
        <>
          <p
            className={cn(
              "mt-2 text-xs text-muted-foreground leading-relaxed",
              !expanded && "line-clamp-2",
            )}
          >
            {paper.abstract}
          </p>
          {paper.abstract.length > 120 && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="mt-1 text-xs text-primary hover:underline"
            >
              {expanded ? "Show less" : "Show more"}
            </button>
          )}
        </>
      )}
    </div>
  );
}

function PaperSection({
  label,
  icon,
  papers,
}: {
  label: string;
  icon: React.ReactNode;
  papers: S2Paper[];
}) {
  if (papers.length === 0) return null;
  return (
    <section>
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
        {icon}
        {label}
        <Badge variant="secondary" className="ml-auto text-xs">{papers.length}</Badge>
      </h3>
      <div className="space-y-2">
        {papers.map((p) => (
          <PaperCard key={p.paper_id || p.doi || p.title} paper={p} />
        ))}
      </div>
    </section>
  );
}

export function PaperRelatedTab({ fileId }: { fileId: number }) {
  const { data, isLoading, isError, error } = useQuery<RelatedBundle, Error>({
    queryKey: ["related", fileId],
    queryFn: () => fetchRelated(fileId),
    staleTime: 7 * 24 * 60 * 60 * 1000, // 7 days — server-side cache matches
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16 text-muted-foreground gap-2">
        <Loader2 className="size-4 animate-spin" />
        <span className="text-sm">Loading related papers…</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <AlertCircle className="size-8 text-muted-foreground/50" />
        <p className="text-sm font-medium">Related papers temporarily unavailable</p>
        <p className="text-xs text-muted-foreground max-w-xs">
          {error.message.includes("unavailable")
            ? "Semantic Scholar is currently unreachable. Try again later."
            : "No related papers found for this document."}
        </p>
      </div>
    );
  }

  if (!data) return null;
  const total =
    (data.related?.length ?? 0) +
    (data.citing?.length ?? 0) +
    (data.recommended?.length ?? 0);

  if (total === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <BookOpen className="size-8 text-muted-foreground/50" />
        <p className="text-sm text-muted-foreground">
          No related papers found. This paper may not yet be indexed by Semantic Scholar.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PaperSection
        label="Recommended"
        icon={<Sparkles className="size-4 text-primary" />}
        papers={data.recommended ?? []}
      />
      <PaperSection
        label="References"
        icon={<BookOpen className="size-4 text-muted-foreground" />}
        papers={data.related ?? []}
      />
      <PaperSection
        label="Cited by"
        icon={<Quote className="size-4 text-muted-foreground" />}
        papers={data.citing ?? []}
      />
      {data.cached_at && (
        <p className="text-center text-xs text-muted-foreground/60">
          Via Semantic Scholar · cached {new Date(data.cached_at).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}
