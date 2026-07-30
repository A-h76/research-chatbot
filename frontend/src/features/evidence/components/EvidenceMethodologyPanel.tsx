import { useQuery } from "@tanstack/react-query";
import { Download, FlaskConical, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { evidenceApi } from "../api";
import type { MethodologyCard } from "../types";

const KIND_LABEL: Record<string, string> = {
  study_design: "Study design",
  dataset: "Dataset",
  variables: "Variables",
  statistics: "Statistics",
  threats_to_validity: "Threats to validity",
};

/** RI-008 — advisory methodology cards (not commands). */
export function EvidenceMethodologyPanel({ projectId }: { projectId: number | null }) {
  const enabled = projectId != null;
  const q = useQuery({
    queryKey: ["evidence", "methodology", projectId],
    queryFn: () => evidenceApi.methodology(projectId as number),
    enabled,
  });

  if (!enabled) {
    return (
      <EmptyState
        icon={<FlaskConical className="size-7" />}
        title="Select a project"
        description="Open a project for methodology advice grounded in its evidence."
      />
    );
  }

  if (q.isLoading) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Reviewing methods…
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
        Could not load methodology advice. Extract evidence first.
      </p>
    );
  }

  const data = q.data;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[12px] text-muted-foreground">
          {data.metrics.card_count} advisory cards · {data.metrics.design_variety} designs ·{" "}
          {data.metrics.evidence_count} evidence
        </p>
        <Button
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-[12px]"
          onClick={() =>
            window.open(
              evidenceApi.methodologyExportUrl(projectId as number),
              "_blank",
              "noopener,noreferrer",
            )
          }
        >
          <Download className="size-3.5" /> Markdown
        </Button>
      </div>

      <p className="text-[11px] italic text-muted-foreground">{data.disclaimer}</p>

      {!data.cards.length ? (
        <EmptyState
          icon={<FlaskConical className="size-7" />}
          title="No methodology signals yet"
          description="Study types, datasets, and limitations will appear after evidence extract."
        />
      ) : (
        <ul className="space-y-2">
          {data.cards.map((card: MethodologyCard) => (
            <li key={card.id} className="rounded-lg border border-border bg-card px-3 py-2.5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-[13px] font-medium text-foreground">{card.title}</h3>
                <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  {KIND_LABEL[card.kind] || card.kind}
                </span>
              </div>
              <p className="mt-1 text-[12px] text-foreground/90">{card.advice}</p>
              {card.evidence_ids?.length ? (
                <p className="mt-1 text-[10px] text-muted-foreground/80">
                  e:{card.evidence_ids.slice(0, 10).join(",")}
                  {card.evidence_ids.length > 10 ? "…" : ""}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {Object.keys(data.design_summary.counts || {}).length ? (
        <p className="text-[11px] text-muted-foreground">
          Designs:{" "}
          {Object.entries(data.design_summary.counts)
            .map(([k, v]) => `${k} (${v})`)
            .join(" · ")}
        </p>
      ) : null}
    </div>
  );
}
