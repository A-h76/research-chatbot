import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ChevronDown, ChevronRight, Download, Loader2, Table2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { evidenceApi } from "../api";
import type { MatrixCell, MatrixRow } from "../types";
import { ConsensusConflictStrip } from "./ConsensusConflictStrip";
import { useProjectConsensusConflict } from "../hooks/useProjectConsensusConflict";

function CellView({ cell }: { cell: MatrixCell }) {
  if (cell.status === "unknown" || !cell.value) {
    return (
      <Link
        to="/research/compare?tab=extract"
        className="text-[11px] font-medium text-amber-800/90 hover:underline dark:text-amber-400/90"
      >
        Not extracted
      </Link>
    );
  }
  return (
    <div className="space-y-0.5">
      <p className="text-[13px] leading-relaxed text-foreground/90">{cell.value}</p>
      {cell.evidence_ids.length > 0 ? (
        <p className="text-[10px] text-muted-foreground">
          {cell.evidence_ids.length} evidence link
          {cell.evidence_ids.length === 1 ? "" : "s"}
        </p>
      ) : cell.sources.includes("paper_analysis") ? (
        <p className="text-[10px] text-muted-foreground">from paper analysis</p>
      ) : null}
    </div>
  );
}

function cellTone(cell: MatrixCell): "known" | "partial" | "missing" {
  if (cell.status === "unknown" || !cell.value) return "missing";
  if (cell.status === "partial") return "partial";
  return "known";
}

function coverageLabel(coverage: number | null | undefined): string {
  if (coverage == null) return "—";
  return `${Math.round(coverage * 100)}% cells known`;
}

function MatrixPaperCard({ row }: { row: MatrixRow }) {
  const [open, setOpen] = useState(false);
  const fields = [
    { key: "method", label: "Method", cell: row.method },
    { key: "dataset", label: "Dataset", cell: row.dataset },
    { key: "findings", label: "Findings", cell: row.findings },
    { key: "limitations", label: "Limitations", cell: row.limitations },
  ] as const;
  const missing = fields.filter((f) => cellTone(f.cell) === "missing").length;
  const known = fields.filter((f) => cellTone(f.cell) === "known").length;

  return (
    <article
      className={cn(
        "rounded-lg border border-border bg-card transition-colors",
        missing === 4 && "border-amber-500/25",
        known === 4 && "border-emerald-500/20",
      )}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-2 px-3 py-2.5 text-left hover:bg-muted/30"
      >
        <span className="mt-0.5 text-muted-foreground">
          {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
        </span>
        <div className="min-w-0 flex-1">
          <Link
            to={`/papers/${row.file_id}`}
            onClick={(e) => e.stopPropagation()}
            className="text-[14px] font-semibold tracking-tight text-foreground hover:text-primary hover:underline"
          >
            {row.paper_title}
          </Link>
          <p className="mt-0.5 text-[12px] text-muted-foreground">
            {[row.paper_year, row.evidence_count ? `${row.evidence_count} evidence` : "No evidence"]
              .filter(Boolean)
              .join(" · ")}
            {missing > 0 ? ` · ${missing} field${missing === 1 ? "" : "s"} missing` : " · Complete"}
          </p>
          {!open ? (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {fields.map(({ key, label, cell }) => {
                const tone = cellTone(cell);
                return (
                  <span
                    key={key}
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full border px-1.5 py-px text-[10px] font-medium",
                      tone === "known" &&
                        "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
                      tone === "partial" &&
                        "border-border bg-muted/50 text-muted-foreground",
                      tone === "missing" &&
                        "border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-400",
                    )}
                  >
                    <span
                      className={cn(
                        "size-1.5 rounded-full",
                        tone === "known" && "bg-emerald-500",
                        tone === "partial" && "bg-muted-foreground/50",
                        tone === "missing" && "bg-amber-500",
                      )}
                      aria-hidden
                    />
                    {label}
                  </span>
                );
              })}
            </div>
          ) : null}
        </div>
      </button>

      {open ? (
        <div className="space-y-3 border-t border-border/70 px-3 py-3 sm:px-4">
          {fields.map(({ key, label, cell }) => (
            <div
              key={key}
              className={cn(
                "rounded-md border border-transparent px-2 py-1.5",
                cellTone(cell) === "missing" &&
                  "border-amber-500/20 bg-amber-500/[0.04]",
                cellTone(cell) === "partial" && "bg-muted/20",
              )}
            >
              <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                {label}
              </p>
              <div className="mt-1">
                <CellView cell={cell} />
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </article>
  );
}

/** RI-002 — Evidence Matrix as expandable paper cards (not a spreadsheet wall). */
export function EvidenceMatrixPanel({
  projectId,
  fileIds,
}: {
  projectId: number | null;
  fileIds?: number[];
}) {
  const enabled = projectId != null;
  const q = useQuery({
    queryKey: ["evidence", "matrix", projectId, fileIds?.join(",") ?? ""],
    queryFn: () =>
      evidenceApi.matrix(projectId as number, {
        file_ids: fileIds?.length ? fileIds : undefined,
      }),
    enabled,
  });
  const ri = useProjectConsensusConflict({
    projectId,
    fileIds,
    enabled,
  });

  if (!enabled) {
    return (
      <EmptyState
        icon={<Table2 className="size-7" />}
        title="Select a project"
        description="Open a project to build the evidence matrix from its papers."
      />
    );
  }

  if (q.isLoading) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Building matrix…
        </div>
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-lg" />
        ))}
      </div>
    );
  }

  if (q.isError || !q.data) {
    return (
      <p className="text-[13px] text-muted-foreground">
        Could not load the evidence matrix. Extract evidence and retry.
      </p>
    );
  }

  const data = q.data;
  if (!data.rows.length) {
    return (
      <EmptyState
        icon={<Table2 className="size-7" />}
        title="No papers in this project"
        description="Upload and analyse papers, then extract evidence to fill the matrix."
      />
    );
  }

  function download(format: "markdown" | "csv") {
    if (projectId == null) return;
    const url = evidenceApi.matrixExportUrl(projectId, format, {
      file_ids: fileIds?.length ? fileIds : undefined,
    });
    window.open(url, "_blank", "noopener,noreferrer");
  }

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
          What every paper says · {data.metrics.paper_count} papers ·{" "}
          {data.metrics.papers_with_evidence} with evidence ·{" "}
          {coverageLabel(data.metrics.coverage)}
          {" · "}
          <Link to="/research/compare?tab=extract" className="text-primary hover:underline">
            Structured Evidence
          </Link>
        </p>
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-[12px]"
            onClick={() => download("markdown")}
          >
            <Download className="size-3.5" /> Markdown
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 gap-1.5 text-[12px]"
            onClick={() => download("csv")}
          >
            <Download className="size-3.5" /> CSV
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {data.rows.map((row: MatrixRow) => (
          <MatrixPaperCard key={row.file_id} row={row} />
        ))}
      </div>
    </div>
  );
}
