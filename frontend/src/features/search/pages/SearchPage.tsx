import { useState, useRef, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, FileText, StickyNote, Quote, MessageSquare,
  Loader2, BookOpen, ChevronRight, X, Filter,
} from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Badge }         from "@/components/ui/badge";
import { Button }        from "@/components/ui/button";
import { EmptyState }    from "@/components/common/EmptyState";
import { useSearch }     from "../useSearch";
import { useUI }         from "@/context/UIContext";
import { cn }            from "@/lib/utils";
import type { SearchResult } from "@/types/api";

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

export function SearchPage() {
  const { currentProjectId }  = useUI();
  const [searchParams, setSearchParams] = useSearchParams();
  const inputRef               = useRef<HTMLInputElement>(null);

  const [q,        setQ]        = useState(searchParams.get("q") ?? "");
  const [kinds,    setKinds]    = useState<Kind[]>(ALL_KINDS);
  const [submitted, setSubmitted] = useState(false);

  const search = useSearch();

  // Auto-run if ?q= was in URL
  useEffect(() => {
    const urlQ = searchParams.get("q");
    if (urlQ && urlQ.length >= 2) {
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

        {/* Kind filter chips */}
        <div className="flex flex-wrap items-center gap-2">
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
        </div>

        {/* Results */}
        {isLoading ? (
          <div className="flex items-center gap-3 py-8 text-muted-foreground">
            <Loader2 className="size-5 animate-spin" />
            <span className="text-sm">Searching…</span>
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
      </div>
    </PageContainer>
  );
}
