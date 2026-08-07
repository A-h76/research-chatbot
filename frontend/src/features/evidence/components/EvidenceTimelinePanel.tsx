import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { ChevronDown, ChevronRight, Download, GitCompare, History, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { useAllFiles } from "@/features/files/useFiles";
import { evidenceApi } from "../api";
import type { TimelineEntry } from "../types";
import { cn } from "@/lib/utils";

const COMPARE_IDS_KEY = "dhund:compare-ids";

function YearBlock({
  entry,
  undated,
  titlesById,
  maxPapers,
  defaultOpen,
  id,
}: {
  entry: TimelineEntry;
  undated?: boolean;
  titlesById: Map<number, string>;
  maxPapers: number;
  defaultOpen?: boolean;
  id?: string;
}) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(defaultOpen ?? false);

  useEffect(() => {
    if (defaultOpen) setOpen(true);
  }, [defaultOpen]);

  const papers = (entry.file_ids ?? []).map((fid) => ({
    id: fid,
    title: titlesById.get(fid) || `Paper ${fid}`,
  }));
  const density = maxPapers > 0 ? Math.max(0.08, entry.paper_count / maxPapers) : 0;

  function compareYear() {
    if (entry.file_ids.length < 2) return;
    try {
      sessionStorage.setItem(COMPARE_IDS_KEY, JSON.stringify(entry.file_ids.slice(0, 10)));
    } catch {
      /* ignore */
    }
    navigate(`/research/compare?tab=compare&ids=${entry.file_ids.slice(0, 10).join(",")}`);
  }

  return (
    <li id={id} className="relative scroll-mt-4 pl-6">
      <span className="absolute left-0 top-1.5 size-2.5 rounded-full border border-border bg-card" />
      <div className="overflow-hidden rounded-lg border border-border bg-card">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-start gap-2 px-3 py-2.5 text-left hover:bg-muted/30"
        >
          <span className="mt-0.5 text-muted-foreground">
            {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-[14px] font-semibold tabular-nums tracking-tight text-foreground">
                {undated ? "Undated" : entry.year}
              </h3>
              <span className="text-[11px] text-muted-foreground">
                {entry.paper_count} paper{entry.paper_count === 1 ? "" : "s"}
                {entry.evidence_count
                  ? ` · ${entry.evidence_count} evidence`
                  : " · 0 evidence"}
              </span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary/60"
                style={{ width: `${Math.round(density * 100)}%` }}
              />
            </div>
            {!open && entry.theme_labels?.length ? (
              <p className="mt-1.5 line-clamp-1 text-[11px] text-muted-foreground">
                {entry.theme_labels.slice(0, 4).join(" · ")}
              </p>
            ) : null}
          </div>
        </button>

        {open ? (
          <div className="space-y-3 border-t border-border px-3 py-2.5">
            {papers.length > 0 ? (
              <ul className="space-y-1">
                {papers.map((p) => (
                  <li key={p.id}>
                    <Link
                      to={`/papers/${p.id}`}
                      className="text-[13px] font-medium text-foreground/90 hover:text-primary hover:underline"
                    >
                      {p.title}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : null}

            {entry.theme_labels?.length ? (
              <div className="flex flex-wrap gap-1">
                {entry.theme_labels.map((label) => (
                  <Link
                    key={label}
                    to="/research/compare?tab=themes"
                    className="rounded-full border border-border bg-muted/40 px-2 py-0.5 text-[10px] text-muted-foreground hover:text-foreground"
                  >
                    {label}
                  </Link>
                ))}
              </div>
            ) : null}

            {entry.study_types?.length ? (
              <p className="text-[11px] text-muted-foreground">
                Designs: {entry.study_types.join(", ")}
              </p>
            ) : null}

            {entry.sample_claims?.length ? (
              <ul className="space-y-1">
                {entry.sample_claims.slice(0, 4).map((s) => (
                  <li key={s.evidence_id} className="text-[12px] leading-relaxed text-foreground/85">
                    {s.claim}
                  </li>
                ))}
              </ul>
            ) : null}

            {entry.file_ids.length >= 2 ? (
              <Button
                size="sm"
                variant="outline"
                className="h-8 gap-1.5 text-[12px]"
                onClick={compareYear}
              >
                <GitCompare className="size-3.5" /> Compare this year
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>
    </li>
  );
}

/** RI-007 — research timeline with year navigation + expandable year cards. */
export function EvidenceTimelinePanel({ projectId }: { projectId: number | null }) {
  const enabled = projectId != null;
  const q = useQuery({
    queryKey: ["evidence", "timeline", projectId],
    queryFn: () => evidenceApi.timeline(projectId as number),
    enabled,
  });
  const { data: allFiles } = useAllFiles();
  const [focusYear, setFocusYear] = useState<number | "undated" | null>(null);

  const titlesById = useMemo(() => {
    const m = new Map<number, string>();
    for (const f of allFiles ?? []) {
      if (projectId != null && f.project_id != null && f.project_id !== projectId) continue;
      m.set(f.id, f.title || f.name);
    }
    return m;
  }, [allFiles, projectId]);

  if (!enabled) {
    return (
      <EmptyState
        icon={<History className="size-7" />}
        title="Select a project"
        description="Open a project to view topic evolution by year."
      />
    );
  }

  if (q.isLoading) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Building timeline…
        </div>
        <Skeleton className="h-40 rounded-lg" />
      </div>
    );
  }

  if (q.isError || !q.data) {
    return (
      <p className="text-[13px] text-muted-foreground">
        Could not load timeline. Add paper years and extract evidence first.
      </p>
    );
  }

  const data = q.data;
  const hasEntries = data.entries.length > 0 || data.undated;
  const maxPapers = Math.max(
    1,
    ...data.entries.map((e) => e.paper_count),
    data.undated?.paper_count ?? 0,
  );

  function jumpTo(year: number | "undated") {
    setFocusYear(year);
    const el = document.getElementById(
      year === "undated" ? "timeline-undated" : `timeline-year-${year}`,
    );
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[12px] text-muted-foreground">
          {data.span.start_year != null
            ? `${data.span.start_year}–${data.span.end_year}`
            : "No dated years"}{" "}
          · {data.metrics.dated_evidence} dated evidence
          {data.metrics.undated_evidence
            ? ` · ${data.metrics.undated_evidence} undated`
            : ""}
        </p>
        <Button
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-[12px]"
          onClick={() =>
            window.open(
              evidenceApi.timelineExportUrl(projectId as number),
              "_blank",
              "noopener,noreferrer",
            )
          }
        >
          <Download className="size-3.5" /> Markdown
        </Button>
      </div>

      {hasEntries && (data.entries.length > 1 || data.undated) ? (
        <div className="flex flex-wrap gap-1">
          {data.entries.map((e) => (
            <button
              key={e.year}
              type="button"
              onClick={() => jumpTo(e.year as number)}
              className={cn(
                "rounded-md border px-2 py-1 text-[11px] tabular-nums",
                focusYear === e.year
                  ? "border-foreground/25 bg-muted font-medium text-foreground"
                  : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              {e.year}
            </button>
          ))}
          {data.undated ? (
            <button
              type="button"
              onClick={() => jumpTo("undated")}
              className={cn(
                "rounded-md border px-2 py-1 text-[11px]",
                focusYear === "undated"
                  ? "border-foreground/25 bg-muted font-medium text-foreground"
                  : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              Undated
            </button>
          ) : null}
        </div>
      ) : null}

      {!hasEntries ? (
        <EmptyState
          icon={<History className="size-7" />}
          title="No timeline anchors"
          description="Set paper years and extract evidence to plot evolution."
        />
      ) : (
        <ol className="relative ml-1.5 space-y-3 border-l border-border">
          {data.entries.map((e, i) => (
            <YearBlock
              key={e.year}
              entry={e}
              titlesById={titlesById}
              maxPapers={maxPapers}
              defaultOpen={i === data.entries.length - 1 || focusYear === e.year}
              id={`timeline-year-${e.year}`}
            />
          ))}
          {data.undated ? (
            <YearBlock
              entry={data.undated}
              undated
              titlesById={titlesById}
              maxPapers={maxPapers}
              defaultOpen={focusYear === "undated"}
              id="timeline-undated"
            />
          ) : null}
        </ol>
      )}

      {data.evolution.length ? (
        <div className="rounded-md border border-dashed border-border px-3 py-2">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Theme span
          </p>
          <ul className="mt-1 space-y-0.5 text-[12px] text-foreground/85">
            {data.evolution.map((s) => (
              <li key={s.theme_id}>
                <Link
                  to="/research/compare?tab=themes"
                  className="hover:text-primary hover:underline"
                >
                  {s.label}
                </Link>
                :{" "}
                <span className="tabular-nums text-muted-foreground">
                  {s.first_year}→{s.last_year}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
