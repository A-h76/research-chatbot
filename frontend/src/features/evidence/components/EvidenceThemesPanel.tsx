import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Download, GitCompare, Loader2, Network, RefreshCw, Table2, Tags } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/common/Toast";
import { ResearchProgressStage } from "@/features/writing/components/ResearchProgressStage";
import { evidenceApi } from "../api";
import type { ThemeCluster } from "../types";
import { cn } from "@/lib/utils";
import { useAllFiles } from "@/features/files/useFiles";

const THEME_MAP_STAGES = [
  "Loading evidence objects",
  "Clustering themes",
  "Assigning papers",
  "Building theme map",
] as const;

const COMPARE_IDS_KEY = "dhund:compare-ids";

type SortKey = "size" | "papers" | "alpha";

function ThemeCard({
  theme,
  titlesById,
  focused,
  onFocus,
}: {
  theme: ThemeCluster;
  titlesById: Map<number, string>;
  focused: boolean;
  onFocus: () => void;
}) {
  const navigate = useNavigate();
  const papers = theme.file_ids.map((id) => ({
    id,
    title: titlesById.get(id) || `Paper ${id}`,
  }));

  function compareTheme() {
    if (theme.file_ids.length < 2) {
      toast.message("Need at least 2 papers in this theme to compare");
      return;
    }
    try {
      sessionStorage.setItem(COMPARE_IDS_KEY, JSON.stringify(theme.file_ids.slice(0, 10)));
    } catch {
      /* ignore */
    }
    navigate(`/research/compare?tab=compare&ids=${theme.file_ids.slice(0, 10).join(",")}`);
  }

  return (
    <li
      className={cn(
        "flex flex-col rounded-lg border bg-card px-3 py-3 transition-colors",
        focused ? "border-primary/40 ring-1 ring-primary/20" : "border-border",
      )}
    >
      <button type="button" onClick={onFocus} className="flex items-start gap-2.5 text-left">
        <span
          className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-[13px] font-semibold text-primary"
          aria-hidden
        >
          {theme.letter || theme.label.slice(0, 1).toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-[14px] font-semibold tracking-tight text-foreground">
            {theme.label}
          </h3>
          <p className="mt-0.5 text-[12px] text-muted-foreground">
            {theme.file_ids.length} paper{theme.file_ids.length === 1 ? "" : "s"} · {theme.size}{" "}
            evidence
          </p>
        </div>
      </button>

      {theme.key_terms.length ? (
        <div className="mt-2.5 flex flex-wrap gap-1">
          {theme.key_terms.slice(0, focused ? 12 : 6).map((t) => (
            <span
              key={t}
              className="rounded-full border border-border bg-muted/40 px-1.5 py-px text-[10px] text-muted-foreground"
            >
              {t}
            </span>
          ))}
        </div>
      ) : null}

      {theme.sample_claims.length ? (
        <div className="mt-3 space-y-1.5">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Key findings
          </p>
          <ul className="space-y-1.5">
            {theme.sample_claims.slice(0, focused ? 6 : 3).map((s) => (
              <li key={s.evidence_id} className="text-[12px] leading-relaxed text-foreground/90">
                {s.claim}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="mt-3 text-[12px] text-muted-foreground">
          No sample claims yet — extract more evidence to enrich this cluster.
        </p>
      )}

      {focused && papers.length > 0 ? (
        <div className="mt-3 space-y-1.5">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Papers in cluster
          </p>
          <ul className="space-y-1">
            {papers.map((p) => (
              <li key={p.id}>
                <Link
                  to={`/papers/${p.id}`}
                  className="text-[12px] font-medium text-foreground/90 hover:text-primary hover:underline"
                >
                  {p.title}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-auto flex flex-wrap gap-1.5 pt-3">
        <Button
          size="sm"
          variant="outline"
          className="h-7 gap-1 px-2 text-[11px]"
          onClick={compareTheme}
          disabled={theme.file_ids.length < 2}
        >
          <GitCompare className="size-3" /> Compare
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-7 gap-1 px-2 text-[11px]"
          onClick={() => navigate("/research/compare?tab=matrix")}
        >
          <Table2 className="size-3" /> Matrix
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-7 gap-1 px-2 text-[11px]"
          onClick={() => navigate("/research/compare?tab=graph")}
        >
          <Network className="size-3" /> Graph
        </Button>
      </div>

      <details className="pt-2">
        <summary className="cursor-pointer text-[11px] text-muted-foreground hover:text-foreground">
          Evidence ({theme.evidence_ids.length})
        </summary>
        <p className="mt-1 text-[10px] text-muted-foreground/80">
          {theme.evidence_ids.slice(0, 24).join(", ")}
          {theme.evidence_ids.length > 24 ? "…" : ""}
        </p>
      </details>
    </li>
  );
}

/** RI-001 / B-615 — project theme discovery panel (+ W6 theme_map job). */
export function EvidenceThemesPanel({ projectId }: { projectId: number | null }) {
  const enabled = projectId != null;
  const qc = useQueryClient();
  const [sortKey, setSortKey] = useState<SortKey>("size");
  const [termQ, setTermQ] = useState("");
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const { data: allFiles } = useAllFiles();
  const titlesById = useMemo(() => {
    const m = new Map<number, string>();
    for (const f of allFiles ?? []) {
      if (projectId != null && f.project_id != null && f.project_id !== projectId) continue;
      m.set(f.id, f.title || f.name);
    }
    return m;
  }, [allFiles, projectId]);

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

  const themesSorted = useMemo(() => {
    const themes = [...(q.data?.themes ?? [])];
    const qTerm = termQ.trim().toLowerCase();
    const filtered = qTerm
      ? themes.filter((t) => {
          const hay = [t.label, ...t.key_terms, ...t.sample_claims.map((c) => c.claim)]
            .join(" ")
            .toLowerCase();
          return hay.includes(qTerm);
        })
      : themes;
    filtered.sort((a, b) => {
      if (sortKey === "papers") return b.file_ids.length - a.file_ids.length;
      if (sortKey === "alpha") return a.label.localeCompare(b.label);
      return b.size - a.size;
    });
    return filtered;
  }, [q.data?.themes, sortKey, termQ]);

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

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={termQ}
          onChange={(e) => setTermQ(e.target.value)}
          placeholder="Filter themes…"
          className="h-8 min-w-[10rem] flex-1 rounded-md border border-border bg-card px-2.5 text-[13px] outline-none placeholder:text-muted-foreground"
        />
        <div className="flex items-center gap-0.5 rounded-md border border-border p-0.5">
          {(
            [
              { key: "size" as const, label: "Evidence" },
              { key: "papers" as const, label: "Papers" },
              { key: "alpha" as const, label: "A–Z" },
            ] as const
          ).map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => setSortKey(key)}
              className={cn(
                "h-7 rounded px-2 text-[11px] font-medium",
                sortKey === key
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {rebuild.isPending ? (
        <ResearchProgressStage
          active
          stages={THEME_MAP_STAGES}
          liveMetric="Waiting on theme_map research job…"
        />
      ) : null}

      {themesSorted.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">
          {termQ.trim()
            ? "No themes match your filter."
            : "No clusters met the minimum size. Add more related evidence or rebuild after extracting more papers."}
        </p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {themesSorted.map((theme: ThemeCluster) => (
            <ThemeCard
              key={theme.id}
              theme={theme}
              titlesById={titlesById}
              focused={focusedId === theme.id}
              onFocus={() =>
                setFocusedId((prev) => (prev === theme.id ? null : theme.id))
              }
            />
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
