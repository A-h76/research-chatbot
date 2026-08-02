import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Download, Loader2, Table2 } from "lucide-react";
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
    return <span className="text-[11px] italic text-muted-foreground">unknown</span>;
  }
  return (
    <div className="space-y-0.5">
      <p className="text-[12px] leading-snug text-foreground/90">{cell.value}</p>
      {cell.evidence_ids.length > 0 ? (
        <p className="text-[10px] text-muted-foreground">
          e:{cell.evidence_ids.slice(0, 5).join(",")}
          {cell.evidence_ids.length > 5 ? "…" : ""}
        </p>
      ) : cell.sources.includes("paper_analysis") ? (
        <p className="text-[10px] text-muted-foreground">from paper analysis</p>
      ) : null}
    </div>
  );
}

function coverageLabel(coverage: number | null | undefined): string {
  if (coverage == null) return "—";
  return `${Math.round(coverage * 100)}% cells known`;
}

/** RI-002 / B-612 — project Evidence Matrix table + export. */
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
          <Skeleton key={i} className="h-14 rounded-lg" />
        ))}
      </div>
    );
  }

  if (q.isError) {
    return (
      <p className="text-[13px] text-muted-foreground">
        Could not load evidence matrix. Try again after extracting evidence from papers.
      </p>
    );
  }

  const data = q.data;
  if (!data?.rows?.length) {
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
          Paper × Method × Dataset × Findings × Limitations ·{" "}
          {data.metrics.paper_count} papers · {data.metrics.papers_with_evidence} with
          evidence · {coverageLabel(data.metrics.coverage)}
          {" · "}
          <Link to="/research/compare?tab=extract" className="text-primary hover:underline">
            Open structured Extract
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

      <div className="overflow-x-auto rounded-lg border border-border bg-card">
        <table className="w-full min-w-[52rem] border-collapse text-left">
          <thead>
            <tr className="border-b border-border bg-muted/30 text-[11px] uppercase tracking-wide text-muted-foreground">
              <th className="px-3 py-2 font-medium">Paper</th>
              <th className="px-3 py-2 font-medium">Method</th>
              <th className="px-3 py-2 font-medium">Dataset</th>
              <th className="px-3 py-2 font-medium">Findings</th>
              <th className="px-3 py-2 font-medium">Limitations</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row: MatrixRow) => (
              <tr key={row.file_id} className="border-b border-border/80 align-top last:border-0">
                <td className="px-3 py-2.5">
                  <p className="text-[12px] font-medium text-foreground">{row.paper_title}</p>
                  <p className="text-[10px] text-muted-foreground">
                    {[row.paper_year, row.evidence_count ? `${row.evidence_count} evidence` : "no evidence"]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </td>
                {(
                  [
                    ["method", row.method],
                    ["dataset", row.dataset],
                    ["findings", row.findings],
                    ["limitations", row.limitations],
                  ] as const
                ).map(([key, cell]) => (
                  <td
                    key={key}
                    className={cn(
                      "max-w-[14rem] px-3 py-2.5",
                      cell.status === "unknown" && "bg-muted/10",
                    )}
                  >
                    <CellView cell={cell} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
