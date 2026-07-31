import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, ChevronRight, Copy, ExternalLink, Search } from "lucide-react";
import { toast } from "@/components/common/Toast";
import { cn } from "@/lib/utils";
import {
  citationSearchBlob,
  type CitationPreview,
} from "../mappers/citationPreview";

const ROW_H = 64;
const LIST_H = 360;
const OVERSCAN = 6;

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
      {children}
    </h3>
  );
}

function highlightMatch(text: string, query: string): React.ReactNode {
  const q = query.trim();
  if (!q) return text;
  const lower = text.toLowerCase();
  const needle = q.toLowerCase();
  const idx = lower.indexOf(needle);
  if (idx < 0) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="rounded-sm bg-primary/15 px-0.5 text-foreground">
        {text.slice(idx, idx + needle.length)}
      </mark>
      {text.slice(idx + needle.length)}
    </>
  );
}

/**
 * Collapsed-by-default bibliography browser — not a Structure outline dump.
 * Phase A: lazy render, search, compact rows, progressive disclosure.
 */
export function ReferenceBrowser({ references }: { references: CitationPreview[] }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return references;
    return references.filter((r) => citationSearchBlob(r).includes(q));
  }, [references, query]);

  useEffect(() => {
    setScrollTop(0);
    if (listRef.current) listRef.current.scrollTop = 0;
  }, [query]);

  if (references.length === 0) return null;

  const count = references.length;
  const useVirtual = open && filtered.length > 40;
  const start = useVirtual
    ? Math.max(0, Math.floor(scrollTop / ROW_H) - OVERSCAN)
    : 0;
  const visibleCount = useVirtual
    ? Math.ceil(LIST_H / ROW_H) + OVERSCAN * 2
    : filtered.length;
  const end = Math.min(filtered.length, start + visibleCount);
  const slice = filtered.slice(start, end);
  const padTop = useVirtual ? start * ROW_H : 0;
  const padBottom = useVirtual ? Math.max(0, (filtered.length - end) * ROW_H) : 0;

  return (
    <section aria-labelledby="structure-references-heading" className="space-y-2">
      <h2 id="structure-references-heading" className="sr-only">
        References
      </h2>

      <button
        type="button"
        className="flex w-full items-start gap-2 rounded-xl border border-border bg-card px-4 py-3 text-left transition-colors hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? (
          <ChevronDown className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        )}
        <span className="min-w-0 flex-1">
          <span className="block text-[14px] font-semibold tracking-tight text-foreground">
            References ({count})
          </span>
          <span className="mt-0.5 block text-[12px] text-muted-foreground">
            {count.toLocaleString()} cited paper{count === 1 ? "" : "s"} · From this manuscript
          </span>
        </span>
      </button>

      {open && (
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          <div className="flex items-center gap-2 border-b border-border px-3 py-2.5">
            <Search className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search author, title, DOI, journal…"
              className="w-full bg-transparent text-[13px] outline-none placeholder:text-muted-foreground"
              aria-label="Search references"
            />
            {query.trim() && (
              <span className="shrink-0 text-[11px] tabular-nums text-muted-foreground">
                {filtered.length} match{filtered.length === 1 ? "" : "es"}
              </span>
            )}
          </div>

          {filtered.length === 0 ? (
            <p className="px-4 py-8 text-center text-[13px] text-muted-foreground">
              No references match “{query.trim()}”.
            </p>
          ) : (
            <div
              ref={listRef}
              className={cn("scrollbar-thin", useVirtual ? "overflow-y-auto" : "")}
              style={useVirtual ? { height: LIST_H } : undefined}
              onScroll={
                useVirtual
                  ? (e) => setScrollTop((e.target as HTMLDivElement).scrollTop)
                  : undefined
              }
            >
              <div style={useVirtual ? { paddingTop: padTop, paddingBottom: padBottom } : undefined}>
                {slice.map((ref) => (
                  <ReferenceRow
                    key={ref.id}
                    citation={ref}
                    query={query}
                    expanded={expandedId === ref.id}
                    onToggle={() =>
                      setExpandedId((id) => (id === ref.id ? null : ref.id))
                    }
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function ReferenceRow({
  citation,
  query,
  expanded,
  onToggle,
}: {
  citation: CitationPreview;
  query: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  const primary = citation.authorsLine ?? citation.titleLine ?? citation.raw;
  const secondary = citation.authorsLine ? citation.titleLine : undefined;
  const meta = [citation.journal, citation.year].filter(Boolean).join(" · ");

  async function copyCitation() {
    try {
      await navigator.clipboard.writeText(citation.raw);
      toast.success("Citation copied");
    } catch {
      toast.error("Could not copy");
    }
  }

  return (
    <div className="border-b border-border/70 last:border-0">
      <button
        type="button"
        className="flex w-full items-start gap-2 px-3 py-2.5 text-left hover:bg-muted/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
        aria-expanded={expanded}
        onClick={onToggle}
      >
        {expanded ? (
          <ChevronDown className="mt-1 size-3.5 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="mt-1 size-3.5 shrink-0 text-muted-foreground" />
        )}
        <span className="min-w-0 flex-1 space-y-0.5">
          <span className="block text-[13px] font-medium leading-snug text-foreground">
            {highlightMatch(primary, query)}
          </span>
          {secondary && (
            <span className="block text-[12px] leading-snug text-muted-foreground">
              {highlightMatch(secondary, query)}
            </span>
          )}
          {meta ? (
            <span className="block text-[11px] text-muted-foreground/90">
              {highlightMatch(meta, query)}
            </span>
          ) : !citation.parsed ? (
            <span className="block text-[11px] text-muted-foreground/80">Raw citation</span>
          ) : null}
        </span>
      </button>

      {expanded && (
        <div className="space-y-3 border-t border-border/60 bg-muted/15 px-3 py-3 pl-9">
          <p className="text-[12px] leading-relaxed text-foreground/90 whitespace-pre-wrap break-words">
            {citation.raw}
          </p>
          {(citation.authorsLine || citation.journal || citation.year || citation.doi) && (
            <dl className="grid gap-1.5 text-[12px] sm:grid-cols-[5.5rem_1fr]">
              {citation.authorsLine && (
                <>
                  <dt className="text-muted-foreground">Authors</dt>
                  <dd className="text-foreground/90">{citation.authorsLine}</dd>
                </>
              )}
              {citation.journal && (
                <>
                  <dt className="text-muted-foreground">Journal</dt>
                  <dd className="text-foreground/90">{citation.journal}</dd>
                </>
              )}
              {citation.year != null && (
                <>
                  <dt className="text-muted-foreground">Year</dt>
                  <dd className="text-foreground/90">{citation.year}</dd>
                </>
              )}
              {citation.doi && (
                <>
                  <dt className="text-muted-foreground">DOI</dt>
                  <dd className="break-all text-foreground/90">{citation.doi}</dd>
                </>
              )}
            </dl>
          )}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="inline-flex h-7 items-center gap-1.5 rounded-md border border-border bg-background px-2.5 text-[11px] font-medium hover:bg-muted"
              onClick={(e) => {
                e.stopPropagation();
                void copyCitation();
              }}
            >
              <Copy className="size-3" />
              Copy citation
            </button>
            {citation.doi && (
              <a
                href={`https://doi.org/${citation.doi}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-7 items-center gap-1.5 rounded-md border border-border bg-background px-2.5 text-[11px] font-medium hover:bg-muted"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="size-3" />
                Open DOI
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// silence unused in case tree-shaking — SectionHeading reserved for consistency
void SectionHeading;
void Check;
