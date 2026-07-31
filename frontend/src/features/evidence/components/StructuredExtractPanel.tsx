import { useQuery } from "@tanstack/react-query";
import { Download, Loader2, ClipboardList } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { evidenceApi } from "../api";
import type { ExtractCell, StructuredExtractRow } from "../types";

function CellView({ cell }: { cell: ExtractCell }) {
  if (cell.status === "unknown" || !cell.value) {
    return <span className="text-[11px] italic text-muted-foreground">unknown</span>;
  }
  return <p className="text-[12px] leading-snug text-foreground/90">{cell.value}</p>;
}

/** W5 — PICO / methods / outcomes table from medical_understanding. */
export function StructuredExtractPanel({
  projectId,
  fileIds,
}: {
  projectId: number | null;
  fileIds?: number[];
}) {
  const enabled = projectId != null;
  const q = useQuery({
    queryKey: ["research", "extract-table", projectId, fileIds?.join(",") ?? ""],
    queryFn: () =>
      evidenceApi.extractTable(projectId as number, {
        file_ids: fileIds?.length ? fileIds : undefined,
      }),
    enabled,
  });

  if (!enabled) {
    return (
      <EmptyState
        icon={<ClipboardList className="size-7" />}
        title="Select a project"
        description="Open a project to build a structured PICO / methods extract from analysed papers."
      />
    );
  }

  if (q.isLoading) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Building structured extract…
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-14 rounded-lg" />
        ))}
      </div>
    );
  }

  if (q.isError) {
    return (
      <p className="text-[13px] text-muted-foreground">
        Could not load structured extract. Run Phase 1 analysis on papers first.
      </p>
    );
  }

  const data = q.data;
  if (!data || data.rows.length === 0) {
    return (
      <EmptyState
        icon={<ClipboardList className="size-7" />}
        title="No papers yet"
        description="Upload and analyse papers in this project to populate PICO, methods, and outcomes."
      />
    );
  }

  const exportOpts = fileIds?.length ? { file_ids: fileIds } : undefined;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[12px] text-muted-foreground">
          {data.metrics.filled_rows}/{data.metrics.paper_count} papers with extract · coverage{" "}
          {Math.round((data.metrics.coverage || 0) * 100)}%
        </p>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5"
            onClick={() =>
              window.open(
                evidenceApi.extractTableExportUrl(projectId, "markdown", exportOpts),
                "_blank",
                "noopener,noreferrer",
              )
            }
          >
            <Download className="size-3.5" /> Markdown
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5"
            onClick={() =>
              window.open(
                evidenceApi.extractTableExportUrl(projectId, "csv", exportOpts),
                "_blank",
                "noopener,noreferrer",
              )
            }
          >
            <Download className="size-3.5" /> CSV
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="min-w-full text-left text-[12px]">
          <thead className="border-b border-border bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">Paper</th>
              <th className="px-3 py-2 font-medium">Population</th>
              <th className="px-3 py-2 font-medium">Intervention</th>
              <th className="px-3 py-2 font-medium">Comparator</th>
              <th className="px-3 py-2 font-medium">Outcomes</th>
              <th className="px-3 py-2 font-medium">Design</th>
              <th className="px-3 py-2 font-medium">Methods</th>
              <th className="px-3 py-2 font-medium">Findings</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row: StructuredExtractRow) => (
              <tr key={row.file_id} className="border-b border-border/70 align-top">
                <td className="px-3 py-2">
                  <p className="font-medium text-foreground/90">
                    {row.paper_title}
                    {row.paper_year ? ` (${row.paper_year})` : ""}
                  </p>
                  {row.status === "empty" ? (
                    <p className="text-[10px] text-muted-foreground">No medical extract yet</p>
                  ) : null}
                </td>
                <td className="px-3 py-2">
                  <CellView cell={row.population} />
                </td>
                <td className="px-3 py-2">
                  <CellView cell={row.intervention} />
                </td>
                <td className="px-3 py-2">
                  <CellView cell={row.comparator} />
                </td>
                <td className="px-3 py-2">
                  <CellView cell={row.outcomes} />
                </td>
                <td className="px-3 py-2">
                  <CellView cell={row.study_design} />
                </td>
                <td className="px-3 py-2">
                  <CellView cell={row.methods} />
                </td>
                <td className="px-3 py-2">
                  <CellView cell={row.key_findings} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
