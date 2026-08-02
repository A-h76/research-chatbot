import { useState, useRef, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  Search, FileText, StickyNote, Quote, MessageSquare,
  Loader2, BookOpen, ChevronRight, X, Filter, Sparkles,
  Globe, ExternalLink, Plus, Check,
} from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Badge }         from "@/components/ui/badge";
import { Button }        from "@/components/ui/button";
import { EmptyState }    from "@/components/common/EmptyState";
import { useSearch, useAskAi } from "../useSearch";
import { useUI }         from "@/context/UIContext";
import { cn }            from "@/lib/utils";
import type { SearchResult, UserFile } from "@/types/api";
import { discoverWorks, type OpenAlexWork } from "../discoverApi";
import { formatApiFailure } from "@/lib/apiErrors";
import { ResearchProgressStage } from "@/features/writing/components/ResearchProgressStage";

const LIBRARY_ASK_STAGES = [
  "Searching your library",
  "Organising evidence",
  "Drafting grounded answer",
] as const;

interface DiscoverImportResult {
  already_exists: boolean;
  file: UserFile;
}

async function importDiscoverWork(
  work: OpenAlexWork,
  projectId: number | null,
): Promise<DiscoverImportResult> {
  const res = await fetch("/api/discover/import", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      doi: work.doi,
      title: work.title,
      authors: work.authors,
      year: work.year,
      venue: work.venue,
      abstract: work.abstract,
      open_access_url: work.open_access_url,
      openalex_id: work.id,
      project_id: projectId,
    }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || body.error || "import_failed");
  }
  return res.json();
}

function DiscoverCard({
  work,
  projectId,
}: {
  work: OpenAlexWork;
  projectId: number | null;
}) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const [importState, setImportState] = useState<"idle" | "adding" | "added" | "exists" | "error">("idle");
  const [importedId, setImportedId] = useState<number | null>(null);
  const [importError, setImportError] = useState("");
  const href = work.doi
    ? `https://doi.org/${work.doi}`
    : work.open_access_url || null;

  async function handleAdd() {
    if (importState === "adding" || importState === "added" || importState === "exists") return;
    setImportState("adding");
    setImportError("");
    try {
      const result = await importDiscoverWork(work, projectId);
      setImportedId(result.file.id);
      setImportState(result.already_exists ? "exists" : "added");
    } catch (err) {
      setImportState("error");
      setImportError(err instanceof Error ? err.message : "Could not add to library");
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className="rounded-2xl border border-border bg-card p-4 shadow-sm hover:border-primary/30 transition-colors"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium leading-snug text-foreground">{work.title || "Untitled"}</p>
          {work.authors && (
            <p className="mt-1 text-xs text-muted-foreground truncate">{work.authors}</p>
          )}
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            {work.year && <span className="text-xs text-muted-foreground">{work.year}</span>}
            {work.venue && (
              <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                · {work.venue}
              </span>
            )}
            {work.citation_count > 0 && (
              <Badge variant="secondary" className="text-xs gap-1 py-0">
                <Quote className="size-3" />
                {work.citation_count.toLocaleString()}
              </Badge>
            )}
          </div>
          {work.concepts.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {work.concepts.slice(0, 4).map((c) => (
                <span key={c} className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground">
                  {c}
                </span>
              ))}
            </div>
          )}
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
      {work.abstract && (
        <>
          <p className={cn("mt-2 text-xs text-muted-foreground leading-relaxed", !expanded && "line-clamp-2")}>
            {work.abstract}
          </p>
          {work.abstract.length > 120 && (
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
    </motion.div>
  );
}

function DiscoverPanel({ query, projectId }: { query: string; projectId: number | null }) {
  const [page, setPage] = useState(1);
  const trimmed = query.trim();

  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey: ["discover", trimmed, page],
    queryFn: () => discoverWorks(trimmed, page),
    enabled: trimmed.length >= 2,
    staleTime: 30 * 60 * 1000, // 30 min
    retry: 1,
  });

  if (trimmed.length < 2) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <Globe className="size-8 text-muted-foreground/40" />
        <p className="text-sm text-muted-foreground">Type at least 2 characters to discover papers.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        <span className="text-sm">Searching OpenAlex…</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-muted-foreground">
          {formatApiFailure(
            error,
            "Discover is temporarily unavailable. Try again later.",
          )}
        </p>
      </div>
    );
  }

  const works = data?.results ?? [];

  if (works.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-muted-foreground">No papers found for "{trimmed}".</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        Via OpenAlex · page {page}
        {isFetching && <Loader2 className="ml-1 inline size-3 animate-spin" />}
      </p>
      {works.map((w) => (
        <DiscoverCard key={w.id || w.doi || w.title} work={w} projectId={projectId} />
      ))}
      <div className="flex justify-center gap-2 pt-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1 || isFetching}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPage((p) => p + 1)}
          disabled={works.length < 15 || isFetching}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

// ── Ask AI (RAG) panel ───────────────────────────────────────────────────────
function AskAiPanel({ query, projectId }: { query: string; projectId: number | null }) {
  const navigate = useNavigate();
  const askAi = useAskAi();

  return (
    <div className="space-y-3 rounded-2xl border border-primary/15 bg-accent-soft/40 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Sparkles className="size-4 text-primary" />
          Ask from library
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => askAi.mutate({ query: query.trim(), project_id: projectId })}
          disabled={query.trim().length < 2 || askAi.isPending}
          className="gap-1.5"
        >
          {askAi.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}
          {askAi.isPending ? "Searching library…" : "Ask from library"}
        </Button>
      </div>

      {askAi.isPending ? (
        <ResearchProgressStage
          active
          stages={LIBRARY_ASK_STAGES}
          liveMetric="Grounding the answer in papers you already imported"
        />
      ) : null}

      {askAi.isError && (
        <p className="text-sm text-destructive">
          {askAi.error instanceof Error ? askAi.error.message : "Ask AI failed"}
        </p>
      )}

      {askAi.data && (
        askAi.data.answer ? (
          <div className="space-y-3">
            <p className="text-sm leading-relaxed">{askAi.data.answer}</p>
            {askAi.data.sources.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {askAi.data.sources.map((s) => (
                  <button
                    key={s.chunk_id}
                    onClick={() => navigate(`/papers/${s.document_id}`)}
                    className="inline-flex items-center gap-1 rounded-full border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground hover:border-primary/30 hover:text-foreground transition-colors"
                    title={s.title}
                  >
                    <FileText className="size-3" />
                    <span className="max-w-[16ch] truncate">{s.title}</span>
                    <span className="tabular-nums opacity-70">{Math.round(s.score * 100)}%</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            {askAi.data.message || "No relevant documents found for this query."}
          </p>
        )
      )}
    </div>
  );
}

// ── Kind config ───────────────────────────────────────────────────────────────
type Kind = "paper" | "note" | "citation" | "chat";

const KIND_CONFIG: Record<Kind, { label: string; icon: React.ReactNode; color: string }> = {
  paper:    { label: "Papers",    icon: <FileText className="size-3.5" />,     color: "text-primary" },
  note:     { label: "Notes",     icon: <StickyNote className="size-3.5" />,   color: "text-amber-600 dark:text-amber-400" },
  citation: { label: "Citations", icon: <Quote className="size-3.5" />,         color: "text-emerald-600 dark:text-emerald-400" },
  chat:     { label: "Chats",     icon: <MessageSquare className="size-3.5" />, color: "text-blue-600 dark:text-blue-400" },
};

// ── Result card ───────────────────────────────────────────────────────────────
function ResultCard({ result }: { result: SearchResult }) {
  const navigate = useNavigate();
  const cfg      = KIND_CONFIG[result.kind];

  return (
    <motion.button
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      onClick={() => navigate(result.url)}
      className="flex w-full items-start gap-3 rounded-2xl border border-border bg-card p-4 text-left shadow-sm hover:border-primary/30 hover:shadow-md transition-all"
    >
      {/* Kind icon */}
      <div className={cn(
        "flex size-9 shrink-0 items-center justify-center rounded-xl",
        result.kind === "paper"    ? "bg-accent-soft"
        : result.kind === "note"  ? "bg-amber-50 dark:bg-amber-950/40"
        : result.kind === "chat"  ? "bg-blue-50 dark:bg-blue-950/40"
        : "bg-emerald-50 dark:bg-emerald-950/40",
      )}>
        <span className={cfg.color}>{cfg.icon}</span>
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={cn("text-[10px] font-semibold uppercase tracking-wider", cfg.color)}>
            {cfg.label}
          </span>
          {result.section && (
            <span className="text-[10px] text-muted-foreground">
              § {result.section}
            </span>
          )}
          {result.page && (
            <span className="text-[10px] text-muted-foreground">
              p. {result.page}
            </span>
          )}
          <span className="ml-auto text-[10px] text-muted-foreground tabular-nums">
            {Math.round(result.score * 100)}% match
          </span>
        </div>

        <p className="text-sm font-medium leading-snug truncate" title={result.title}>
          {result.title}
        </p>

        {result.file_name && result.file_name !== result.title && (
          <p className="text-xs text-muted-foreground truncate">{result.file_name}</p>
        )}

        <p className="text-xs leading-relaxed text-muted-foreground line-clamp-2">
          {result.snippet}
        </p>
      </div>

      <ChevronRight className="size-4 shrink-0 self-center text-muted-foreground/50" />
    </motion.button>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
const ALL_KINDS: Kind[] = ["paper", "note", "citation", "chat"];

type SearchMode = "library" | "discover";

export function SearchPage() {
  const { currentProjectId }  = useUI();
  const [searchParams, setSearchParams] = useSearchParams();
  const inputRef               = useRef<HTMLInputElement>(null);

  const [mode,     setMode]     = useState<SearchMode>(
    searchParams.get("mode") === "discover" ? "discover" : "library",
  );
  const [q,        setQ]        = useState(searchParams.get("q") ?? "");
  const [kinds,    setKinds]    = useState<Kind[]>(ALL_KINDS);
  const [submitted, setSubmitted] = useState(false);

  const search = useSearch();

  // Auto-run if ?q= was in URL (library mode only — discover uses its own query)
  useEffect(() => {
    const urlQ = searchParams.get("q");
    const urlMode = searchParams.get("mode");
    if (urlMode === "discover") setMode("discover");
    if (urlQ && urlQ.length >= 2 && urlMode !== "discover") {
      setQ(urlQ);
      search.mutate({ q: urlQ, kinds, project_id: currentProjectId });
      setSubmitted(true);
    }
    inputRef.current?.focus();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function run(query = q) {
    if (query.trim().length < 2) return;
    setSearchParams(query ? { q: query } : {});
    search.mutate({ q: query.trim(), kinds, project_id: currentProjectId });
    setSubmitted(true);
  }

  function toggleKind(k: Kind) {
    setKinds((prev) =>
      prev.includes(k)
        ? prev.length > 1 ? prev.filter((x) => x !== k) : prev   // keep at least 1
        : [...prev, k],
    );
  }

  const results  = search.data?.results ?? [];
  const total    = search.data?.total   ?? 0;
  const isLoading = search.isPending;

  // Group by kind for display
  const grouped: Record<Kind, SearchResult[]> = {
    paper: [], note: [], citation: [], chat: [],
  };
  for (const r of results) grouped[r.kind as Kind]?.push(r);

  return (
    <PageContainer
      title="Search"
      description="Find anything across your papers, notes, citations, and chats."
    >
      <div className="space-y-6">

        {/* Mode tabs */}
        <div className="flex gap-1 rounded-xl border border-border bg-muted/30 p-1 w-fit">
          {(["library", "discover"] as SearchMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-sm font-medium transition-all",
                mode === m
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {m === "library" ? <Search className="size-3.5" /> : <Globe className="size-3.5" />}
              {m === "library" ? "My Library" : "Discover"}
            </button>
          ))}
        </div>

        {/* Search bar */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              ref={inputRef}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run()}
              placeholder="Search your research…"
              className="w-full rounded-xl border border-border bg-card pl-10 pr-10 py-3 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/20"
            />
            {q && (
              <button
                onClick={() => { setQ(""); setSubmitted(false); search.reset(); }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="size-4" />
              </button>
            )}
          </div>
          <Button onClick={() => run()} disabled={q.trim().length < 2 || isLoading} className="gap-2">
            {isLoading ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
            Search
          </Button>
        </div>

        {/* Kind filter chips — library mode only */}
        {mode === "library" && <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Filter className="size-3" /> Filter:
          </span>
          {ALL_KINDS.map((k) => {
            const cfg     = KIND_CONFIG[k];
            const active  = kinds.includes(k);
            const count   = grouped[k].length;
            return (
              <button
                key={k}
                onClick={() => toggleKind(k)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-all",
                  active
                    ? "border-primary bg-accent-soft text-primary"
                    : "border-border text-muted-foreground hover:border-primary/40",
                )}
              >
                <span className={active ? "text-primary" : "text-muted-foreground"}>
                  {cfg.icon}
                </span>
                {cfg.label}
                {submitted && count > 0 && (
                  <span className={cn(
                    "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                    active ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground",
                  )}>
                    {count}
                  </span>
                )}
              </button>
            );
          })}

          {currentProjectId && (
            <Badge variant="outline" className="text-xs gap-1">
              <BookOpen className="size-3" /> Project scope
            </Badge>
          )}
        </div>}

        {mode === "discover" ? (
          /* ── Discover (OpenAlex) ───────────────────────────────────────── */
          <DiscoverPanel query={q} projectId={currentProjectId} />
        ) : (
          /* ── Library (RAG + full-text search) ────────────────────────── */
          <>
            {/* Ask AI (RAG) — independent of the search-results flow above */}
            <AskAiPanel query={q} projectId={currentProjectId} />

            {/* Results */}
            {isLoading ? (
              <div className="flex items-center gap-3 py-8 text-muted-foreground">
                <Loader2 className="size-5 animate-spin" />
                <span className="text-sm">Searching library…</span>
              </div>
            ) : submitted && results.length === 0 ? (
              <EmptyState
                icon={<Search className="size-8" />}
                title="No results found"
                description={`Nothing matched "${search.data?.q ?? q}". Try different keywords or change your filters.`}
              />
            ) : submitted ? (
              <div className="space-y-6">
                <p className="text-xs text-muted-foreground">
                  {total} result{total !== 1 ? "s" : ""} for <span className="font-medium">"{search.data?.q}"</span>
                </p>

                {/* Render by kind group (only non-empty groups shown) */}
                {ALL_KINDS.filter((k) => kinds.includes(k) && grouped[k].length > 0).map((k) => (
                  <section key={k} className="space-y-3">
                    <div className="flex items-center gap-2">
                      <span className={KIND_CONFIG[k].color}>{KIND_CONFIG[k].icon}</span>
                      <h2 className="text-sm font-semibold">{KIND_CONFIG[k].label}</h2>
                      <span className="text-xs text-muted-foreground">({grouped[k].length})</span>
                    </div>
                    <div className="space-y-2">
                      <AnimatePresence>
                        {grouped[k].map((r, i) => (
                          <ResultCard key={`${r.kind}-${r.ref_id}-${i}`} result={r} />
                        ))}
                      </AnimatePresence>
                    </div>
                  </section>
                ))}
              </div>
            ) : (
              <div className="py-12 text-center">
                <Search className="mx-auto mb-4 size-12 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">
                  Type a query and press Enter or click Search.
                </p>
                <p className="mt-1 text-xs text-muted-foreground/70">
                  Searches across papers (semantic), notes, citations, and chats.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </PageContainer>
  );
}
