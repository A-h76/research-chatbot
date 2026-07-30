import { useQuery } from "@tanstack/react-query";
import { Download, Loader2, History } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { evidenceApi } from "../api";
import type { TimelineEntry } from "../types";

function YearBlock({ entry, undated }: { entry: TimelineEntry; undated?: boolean }) {
  return (
    <li className="relative pl-6">
      <span className="absolute left-0 top-1.5 size-2.5 rounded-full border border-border bg-card" />
      <div className="rounded-lg border border-border bg-card px-3 py-2.5">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-[13px] font-medium tabular-nums text-foreground">
            {undated ? "Undated" : entry.year}
          </h3>
          <span className="text-[10px] text-muted-foreground">
            {entry.paper_count} paper{entry.paper_count === 1 ? "" : "s"} · {entry.evidence_count}{" "}
            evidence
          </span>
        </div>
        {entry.theme_labels?.length ? (
          <p className="mt-1 text-[11px] text-muted-foreground">
            Themes: {entry.theme_labels.join("; ")}
          </p>
        ) : null}
        {entry.study_types?.length ? (
          <p className="text-[11px] text-muted-foreground">
            Designs: {entry.study_types.join(", ")}
          </p>
        ) : null}
        {entry.sample_claims?.length ? (
          <ul className="mt-1.5 space-y-0.5">
            {entry.sample_claims.map((s) => (
              <li key={s.evidence_id} className="text-[12px] text-foreground/85">
                <span className="text-muted-foreground">e:{s.evidence_id}</span> {s.claim}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </li>
  );
}

/** RI-007 — research timeline with paper/evidence/theme anchors. */
export function EvidenceTimelinePanel({ projectId }: { projectId: number | null }) {
  const enabled = projectId != null;
  const q = useQuery({
    queryKey: ["evidence", "timeline", projectId],
    queryFn: () => evidenceApi.timeline(projectId as number),
    enabled,
  });

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

      {!hasEntries ? (
        <EmptyState
          icon={<History className="size-7" />}
          title="No timeline anchors"
          description="Set paper years and extract evidence to plot evolution."
        />
      ) : (
        <ol className="relative space-y-3 border-l border-border ml-1.5">
          {data.entries.map((e) => (
            <YearBlock key={e.year} entry={e} />
          ))}
          {data.undated ? <YearBlock entry={data.undated} undated /> : null}
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
                {s.label}:{" "}
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
