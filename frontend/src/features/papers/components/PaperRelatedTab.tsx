/**
 * PaperRelatedTab — Related / Citing / Recommended papers via Semantic Scholar.
 *
 * Fetches from GET /api/files/:id/related.
 * Cache: 7 days server-side; no re-fetch on tab switch until stale.
 * Add to Library reuses POST /api/discover/import (metadata-only stubs).
 * Fails gracefully: shows a neutral "unavailable" message rather than an error.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ExternalLink, BookOpen, Quote, Sparkles, Loader2, AlertCircle, Plus, Check,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useUI } from "@/context/UIContext";
import {
  fetchRelated,
  importRelatedPaper,
  type RelatedBundle,
  type S2Paper,
} from "../relatedApi";

function PaperCard({
  paper,
  projectId,
}: {
  paper: S2Paper;
  projectId: number | null;
}) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const [importState, setImportState] = useState<"idle" | "adding" | "added" | "exists" | "error">("idle");
  const [importedId, setImportedId] = useState<number | null>(null);
  const [importError, setImportError] = useState("");
  const href = paper.doi
    ? `https://doi.org/${paper.doi}`
    : paper.open_access_url || null;

  async function handleAdd() {
    if (importState === "adding" || importState === "added" || importState === "exists") return;
    if (!paper.title && !paper.doi) {
      setImportState("error");
      setImportError("Missing title and DOI");
      return;
    }
    setImportState("adding");
    setImportError("");
    try {
      const result = await importRelatedPaper(paper, projectId);
      setImportedId(result.file.id);
      setImportState(result.already_exists ? "exists" : "added");
    } catch (err) {
      setImportState("error");
      setImportError(err instanceof Error ? err.message : "Could not add to library");
    }
  }

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

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {importState === "added" || importState === "exists" ? (
          <>
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5"
              onClick={() => importedId && navigate(`/papers/${importedId}`)}
              disabled={!importedId}
            >
              <Check className="size-3.5" />
              {importState === "exists" ? "Already in library" : "Added"}
            </Button>
            {importedId && (
              <button
                onClick={() => navigate(`/papers/${importedId}`)}
                className="text-xs text-primary hover:underline"
              >
                Open paper
              </button>
            )}
          </>
        ) : (
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5"
            onClick={handleAdd}
            disabled={importState === "adding"}
          >
            {importState === "adding" ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Plus className="size-3.5" />
            )}
            {importState === "adding" ? "Adding…" : "Add to Library"}
          </Button>
        )}
        {importState === "error" && (
          <p className="text-xs text-destructive">{importError || "Import failed"}</p>
        )}
      </div>
    </div>
  );
}

function PaperSection({
  label,
  hint,
  icon,
  papers,
  projectId,
}: {
  label: string;
  hint?: string;
  icon: React.ReactNode;
  papers: S2Paper[];
  projectId: number | null;
}) {
  if (papers.length === 0) return null;
  return (
    <section>
      <h3 className="mb-1 flex items-center gap-2 text-sm font-semibold text-foreground">
        {icon}
        {label}
        <Badge variant="secondary" className="ml-auto text-xs">{papers.length}</Badge>
      </h3>
      {hint && (
        <p className="mb-3 text-xs text-muted-foreground">{hint}</p>
      )}
      <div className="space-y-2">
        {papers.map((p) => (
          <PaperCard key={p.paper_id || p.doi || p.title} paper={p} projectId={projectId} />
        ))}
      </div>
    </section>
  );
}

export function PaperRelatedTab({ fileId }: { fileId: number }) {
  const { currentProjectId } = useUI();
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
    const msg = error.message || "";
    const disabled = msg.includes("disabled");
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <AlertCircle className="size-8 text-muted-foreground/50" />
        <p className="text-sm font-medium">Related papers temporarily unavailable</p>
        <p className="text-xs text-muted-foreground max-w-xs">
          {disabled
            ? "Semantic Scholar recommendations are turned off for this environment."
            : msg.includes("unavailable") || msg.includes("related_")
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
        label="Newer & recommended"
        hint="Suggested next reads — add any paper to your library as a metadata stub."
        icon={<Sparkles className="size-4 text-primary" />}
        papers={data.recommended ?? []}
        projectId={currentProjectId}
      />
      <PaperSection
        label="References"
        icon={<BookOpen className="size-4 text-muted-foreground" />}
        papers={data.related ?? []}
        projectId={currentProjectId}
      />
      <PaperSection
        label="Cited by"
        icon={<Quote className="size-4 text-muted-foreground" />}
        papers={data.citing ?? []}
        projectId={currentProjectId}
      />
      {data.cached_at && (
        <p className="text-center text-xs text-muted-foreground/60">
          Via Semantic Scholar · cached {new Date(data.cached_at).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}
