import { useQuery } from "@tanstack/react-query";
import { Download, Loader2, Tags } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { evidenceApi } from "../api";
import type { ThemeCluster } from "../types";

/** RI-001 / B-615 — project theme discovery panel. */
export function EvidenceThemesPanel({ projectId }: { projectId: number | null }) {
  const enabled = projectId != null;
  const q = useQuery({
    queryKey: ["evidence", "themes", projectId],
    queryFn: () => evidenceApi.themes(projectId as number),
    enabled,
  });

  if (!enabled) {
    return (
      <EmptyState
        icon={<Tags className="size-7" />}
        title="Select a project"
        description="Open a project to discover themes from its evidence objects."
      />
    );
  }

  if (q.isLoading) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Discovering themes…
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-lg" />
        ))}
      </div>
    );
  }

  if (q.isError) {
    return (
      <p className="text-[13px] text-muted-foreground">
        Could not load themes. Extract evidence from papers first, then retry.
      </p>
    );
  }

  const data = q.data;
  if (!data || (data.themes.length === 0 && data.unassigned.count === 0)) {
    return (
      <EmptyState
        icon={<Tags className="size-7" />}
        title="No evidence to cluster"
        description="Upload papers and run evidence extract to discover Theme A–N clusters."
      />
    );
  }

  function downloadMarkdown() {
    if (projectId == null) return;
    window.open(evidenceApi.themesExportUrl(projectId, "markdown"), "_blank", "noopener,noreferrer");
  }

  const coverage =
    data.metrics.coverage == null ? "—" : `${Math.round(data.metrics.coverage * 100)}% assigned`;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[12px] text-muted-foreground">
          {data.metrics.theme_count} themes · {data.metrics.assigned_evidence} evidence assigned ·{" "}
          {coverage} · hash {(data.run.input_hash || "").slice(0, 10)}…
        </p>
        <Button
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-[12px]"
          onClick={downloadMarkdown}
        >
          <Download className="size-3.5" /> Markdown
        </Button>
      </div>

      {data.themes.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">
          No clusters met the minimum size. Add more related evidence or lower min cluster size.
        </p>
      ) : (
        <ul className="space-y-2">
          {data.themes.map((theme: ThemeCluster) => (
            <li
              key={theme.id}
              className="rounded-lg border border-border bg-card px-3 py-2.5"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-[13px] font-medium text-foreground">{theme.label}</h3>
                <span className="text-[10px] text-muted-foreground">
                  {theme.size} evidence · {theme.file_ids.length} paper
                  {theme.file_ids.length === 1 ? "" : "s"}
                </span>
              </div>
              {theme.key_terms.length ? (
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Terms: {theme.key_terms.join(", ")}
                </p>
              ) : null}
              {theme.sample_claims.length ? (
                <ul className="mt-2 space-y-1">
                  {theme.sample_claims.map((s) => (
                    <li key={s.evidence_id} className="text-[12px] text-foreground/85">
                      <span className="text-muted-foreground">e:{s.evidence_id}</span>{" "}
                      {s.claim}
                    </li>
                  ))}
                </ul>
              ) : null}
              <p className="mt-1.5 text-[10px] text-muted-foreground/80">
                ids: {theme.evidence_ids.slice(0, 12).join(", ")}
                {theme.evidence_ids.length > 12 ? "…" : ""}
              </p>
            </li>
          ))}
        </ul>
      )}

      {data.unassigned.count > 0 ? (
        <div className="rounded-md border border-dashed border-border px-3 py-2">
          <p className="text-[12px] font-medium text-foreground">Unassigned</p>
          <p className="text-[11px] text-muted-foreground">
            {data.unassigned.count} evidence objects did not join a theme (
            {data.unassigned.reason.replace(/_/g, " ")}).
          </p>
        </div>
      ) : null}
    </div>
  );
}
