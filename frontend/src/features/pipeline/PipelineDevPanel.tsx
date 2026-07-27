import { useState } from "react";
import { usePipeline, useStartAnalysis } from "./usePipeline";
import { isPipelineError } from "./errors";
import { PIPELINE_PHASES } from "./types";
import type { PipelinePhaseName } from "./types";

/**
 * Dev-only inspector for Phase 1 pipeline JSON.
 * Must not ship visible UI in production builds (`import.meta.env.DEV`).
 */
export function PipelineDevPanel({ fileId }: { fileId: number }) {
  const [open, setOpen] = useState(false);
  const [phase, setPhase] = useState<PipelinePhaseName>("document_understanding");
  const { pipeline, derived, isLoading, isError, error, refetch, markEnqueued } =
    usePipeline(fileId);
  const start = useStartAnalysis();

  if (!import.meta.env.DEV) return null;

  return (
    <div className="mt-8 rounded-lg border border-dashed border-border bg-muted/30 p-3 text-xs">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="rounded-md border border-border bg-background px-2 py-1 font-medium hover:bg-muted"
          onClick={() => setOpen((o) => !o)}
        >
          {open ? "Hide" : "Show"} pipeline (dev)
        </button>
        <span className="text-muted-foreground">
          uiState={derived.uiState}
          {derived.currentPhase ? ` · current=${derived.currentPhase}` : ""}
          {` · done=${derived.completed.length} remaining=${derived.remaining.length}`}
        </span>
        <button
          type="button"
          className="ml-auto rounded-md border border-border bg-background px-2 py-1 hover:bg-muted disabled:opacity-50"
          disabled={start.isPending}
          onClick={() => {
            start.mutate(
              { documentId: fileId },
              {
                onSuccess: (data) => {
                  if (data.status === "queued") markEnqueued();
                },
              },
            );
          }}
        >
          {start.isPending ? "Starting…" : "POST analyze"}
        </button>
        <button
          type="button"
          className="rounded-md border border-border bg-background px-2 py-1 hover:bg-muted"
          onClick={() => void refetch()}
        >
          Refetch
        </button>
      </div>

      {open && (
        <div className="mt-3 space-y-2">
          {isLoading && <p className="text-muted-foreground">Loading pipeline…</p>}
          {isError && (
            <p className="text-destructive">
              {isPipelineError(error)
                ? `${error.code} (${error.status})`
                : "Failed to load pipeline"}
            </p>
          )}
          {!isLoading && !pipeline && !isError && (
            <p className="text-muted-foreground">No Phase 1 row (absent).</p>
          )}
          {pipeline && (
            <>
              <p className="font-medium">
                status={pipeline.status} · version={pipeline.pipeline_version || "—"} ·
                completed=[{derived.completed.join(", ") || "—"}]
              </p>
              <label className="flex items-center gap-2 text-muted-foreground">
                Focus phase
                <select
                  className="rounded border border-border bg-background px-1 py-0.5"
                  value={phase}
                  onChange={(e) => setPhase(e.target.value as PipelinePhaseName)}
                >
                  {PIPELINE_PHASES.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>
              <pre className="max-h-64 overflow-auto rounded-md bg-background p-2 text-[10px] leading-relaxed">
                {JSON.stringify(
                  {
                    derived,
                    pipeline: {
                      ...pipeline,
                      phase_results: {
                        [phase]: pipeline.phase_results[phase] ?? null,
                        _keys: Object.keys(pipeline.phase_results),
                      },
                    },
                  },
                  null,
                  2,
                )}
              </pre>
            </>
          )}
          {start.isError && (
            <p className="text-destructive">
              analyze failed:{" "}
              {isPipelineError(start.error)
                ? `${start.error.code} (${start.error.status})`
                : "unknown"}
            </p>
          )}
          {start.isSuccess && start.data && (
            <p className="text-muted-foreground">
              last analyze:{" "}
              {start.data.status === "queued"
                ? `queued job ${start.data.job_id}`
                : `sync status=${start.data.status}`}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
