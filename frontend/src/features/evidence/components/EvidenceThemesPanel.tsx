import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Loader2, RefreshCw, Tags } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/common/Toast";
import { ResearchProgressStage } from "@/features/writing/components/ResearchProgressStage";
import { evidenceApi } from "../api";
import type { ThemeCluster } from "../types";

const THEME_MAP_STAGES = [
  "Loading evidence objects",
  "Clustering themes",
  "Assigning papers",
  "Building theme map",
] as const;

/** RI-001 / B-615 — project theme discovery panel (+ W6 theme_map job). */
export function EvidenceThemesPanel({ projectId }: { projectId: number | null }) {
  const enabled = projectId != null;
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["evidence", "themes", projectId],
    queryFn: () => evidenceApi.themes(projectId as number),
    enabled,
  });

  const rebuild = useMutation({
    mutationFn: async () => {
      if (projectId == null) throw new Error("no_project");
      const enqueued = await evidenceApi.enqueueResearchJob(projectId, {
        type: "theme_map",
      });
      if (enqueued.status === "done" && enqueued.result) {
        return { mode: "sync" as const, payload: enqueued };
      }
      if (enqueued.job_id) {
        for (let i = 0; i < 8; i += 1) {
          await new Promise((r) => setTimeout(r, 1000));
          const st = await evidenceApi.researchJob(enqueued.job_id!);
          if (st.status === "done") return { mode: "async" as const, payload: st };
          if (st.status === "failed") {
            throw new Error(st.last_error || "theme_map_failed");
          }
        }
        // Worker may be offline — finish synchronously.
        toast.message("Worker slow — finishing theme map inline");
        return {
          mode: "fallback" as const,
          payload: await evidenceApi.enqueueResearchJob(projectId, {
            type: "theme_map",
            sync: true,
          }),
        };
      }
      return {
        mode: "sync" as const,
        payload: await evidenceApi.enqueueResearchJob(projectId, {
          type: "theme_map",
          sync: true,
        }),
      };
    },
    onSuccess: () => {
      toast.success("Theme map ready");
      qc.invalidateQueries({ queryKey: ["evidence", "themes", projectId] });
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : "Theme map failed");
    },
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
      <div className="space-y-3">
        <p className="text-[13px] text-muted-foreground">
          Could not load themes. Extract evidence from papers first, then retry.
        </p>
        <Button
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-[12px]"
          disabled={rebuild.isPending}
          onClick={() => rebuild.mutate()}
        >
          {rebuild.isPending ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <RefreshCw className="size-3.5" />
          )}
          Rebuild theme map
        </Button>
        {rebuild.isPending ? (
          <ResearchProgressStage active stages={THEME_MAP_STAGES} liveMetric="Queuing theme_map job…" />
        ) : null}
      </div>
    );
  }

  const data = q.data;
  if (!data || (data.themes.length === 0 && data.unassigned.count === 0)) {
    return (
      <div className="space-y-3">
        <EmptyState
          icon={<Tags className="size-7" />}
          title="No evidence to cluster"
          description="Upload papers and run evidence extract, then rebuild the theme map."
        />
        <Button
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 text-[12px]"
          disabled={rebuild.isPending}
          onClick={() => rebuild.mutate()}
        >
          {rebuild.isPending ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <RefreshCw className="size-3.5" />
          )}
          Rebuild theme map
        </Button>
        {rebuild.isPending ? (
          <ResearchProgressStage active stages={THEME_MAP_STAGES} liveMetric="Queuing theme_map job…" />
        ) : null}
      </div>
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
          {coverage}
        </p>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-[12px]"
            disabled={rebuild.isPending}
            onClick={() => rebuild.mutate()}
          >
            {rebuild.isPending ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <RefreshCw className="size-3.5" />
            )}
            Rebuild job
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-[12px]"
            disabled={rebuild.isPending}
            onClick={downloadMarkdown}
          >
            <Download className="size-3.5" /> Markdown
          </Button>
        </div>
      </div>

      {rebuild.isPending ? (
        <ResearchProgressStage
          active
          stages={THEME_MAP_STAGES}
          liveMetric="Waiting on theme_map research job…"
        />
      ) : null}

      {data.themes.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">
          No clusters met the minimum size. Add more related evidence or rebuild after extracting
          more papers.
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
                      {s.claim}
                    </li>
                  ))}
                </ul>
              ) : null}
              <details className="mt-1.5">
                <summary className="cursor-pointer text-[10px] text-muted-foreground/80">
                  Evidence ids ({theme.evidence_ids.length})
                </summary>
                <p className="mt-1 text-[10px] text-muted-foreground/80">
                  {theme.evidence_ids.slice(0, 24).join(", ")}
                  {theme.evidence_ids.length > 24 ? "…" : ""}
                </p>
              </details>
            </li>
          ))}
        </ul>
      )}

      {data.unassigned.count > 0 ? (
        <p className="text-[11px] text-muted-foreground">
          Unassigned: {data.unassigned.count} evidence object
          {data.unassigned.count === 1 ? "" : "s"}
        </p>
      ) : null}
    </div>
  );
}
