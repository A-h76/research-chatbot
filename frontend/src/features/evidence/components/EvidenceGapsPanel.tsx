import { useQuery } from "@tanstack/react-query";
import { Download, Loader2, SearchX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { evidenceApi } from "../api";
import type { ResearchGap } from "../types";
import { cn } from "@/lib/utils";
import { ConsensusConflictStrip } from "./ConsensusConflictStrip";
import { useProjectConsensusConflict } from "../hooks/useProjectConsensusConflict";

const TYPE_LABEL: Record<ResearchGap["type"], string> = {
  thin_theme: "Thin theme",
  missing_matrix_cell: "Missing matrix cell",
  weak_consensus: "Weak consensus",
  unexplained_conflict: "Unexplained conflict",
  coverage: "Coverage",
};

/** RI-006 / B-615 — research gaps from themes + matrix coverage. */
export function EvidenceGapsPanel({ projectId }: { projectId: number | null }) {
  const enabled = projectId != null;
  const q = useQuery({
    queryKey: ["evidence", "gaps", projectId],
    queryFn: () => evidenceApi.gaps(projectId as number),
    enabled,
  });
  const ri = useProjectConsensusConflict({ projectId, enabled });

  if (!enabled) {
    return (
      <EmptyState
        icon={<SearchX className="size-7" />}
        title="Select a project"
        description="Open a project to detect research gaps from evidence coverage."
      />
    );
  }

  if (q.isLoading) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Scanning coverage…
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-lg" />
        ))}
      </div>
    );
  }

  if (q.isError || !q.data) {
    return (
      <p className="text-[13px] text-muted-foreground">
        Could not load research gaps. Extract evidence and retry.
      </p>
    );
  }

  const data = q.data;

  return (
    <div className="space-y-3">
      <ConsensusConflictStrip
        status={ri.status}
        consensus={ri.consensus}
        conflict={ri.conflict}
        compact
      />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[12px] text-muted-foreground">
          {data.metrics.gap_count} gaps · {data.metrics.paper_count} papers ·{" "}
          {data.metrics.evidence_count} evidence
          {data.metrics.mean_density != null
            ? ` · mean density ${Math.round(data.metrics.mean_density * 100)}%`
            : ""}
        </p>
        <Button
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-[12px]"
          onClick={() =>
            window.open(evidenceApi.gapsExportUrl(projectId as number), "_blank", "noopener,noreferrer")
          }
        >
          <Download className="size-3.5" /> Markdown
        </Button>
      </div>

      {!data.gaps.length ? (
        <EmptyState
          icon={<SearchX className="size-7" />}
          title="No coverage gaps flagged"
          description="Themes and matrix cells look covered for this corpus — or evidence is still thin."
        />
      ) : (
        <ul className="space-y-2">
          {data.gaps.map((gap) => (
            <li
              key={gap.id}
              className={cn(
                "rounded-lg border border-border bg-card px-3 py-2.5",
                gap.type === "unexplained_conflict" && "border-rose-700/30",
              )}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  {TYPE_LABEL[gap.type] || gap.type}
                </span>
                <span className="text-[10px] text-muted-foreground">
                  density {Math.round(gap.evidence_density * 100)}%
                </span>
              </div>
              <p className="mt-1 text-[12px] text-foreground/90">{gap.statement}</p>
              {gap.suggested_questions.length ? (
                <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-[11px] text-muted-foreground">
                  {gap.suggested_questions.map((qq) => (
                    <li key={qq}>{qq}</li>
                  ))}
                </ul>
              ) : null}
              {gap.evidence_ids.length ? (
                <p className="mt-1 text-[10px] text-muted-foreground/80">
                  e:{gap.evidence_ids.slice(0, 10).join(",")}
                  {gap.evidence_ids.length > 10 ? "…" : ""}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
