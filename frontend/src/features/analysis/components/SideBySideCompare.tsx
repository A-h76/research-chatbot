import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { evidenceApi } from "@/features/evidence/api";
import type { MatrixCell, MatrixRow } from "@/features/evidence/types";
import { cn } from "@/lib/utils";
import type { UserFile } from "@/types/api";

const DIMENSIONS = [
  { key: "method" as const, label: "Method" },
  { key: "dataset" as const, label: "Dataset" },
  { key: "findings" as const, label: "Findings" },
  { key: "limitations" as const, label: "Limitations" },
];

function cellText(cell: MatrixCell | undefined): { text: string; missing: boolean } {
  if (!cell || cell.status === "unknown" || !cell.value) {
    return { text: "Not extracted", missing: true };
  }
  return { text: cell.value, missing: false };
}

/**
 * Side-by-side paper comparison from Evidence Matrix cells.
 * GitHub-diff style: dimension rows × selected papers as columns.
 */
export function SideBySideCompare({
  projectId,
  files,
  selectedIds,
}: {
  projectId: number | null;
  files: UserFile[];
  selectedIds: number[];
}) {
  const ids = selectedIds.slice(0, 4);
  const enabled = projectId != null && ids.length >= 2;

  const q = useQuery({
    queryKey: ["evidence", "matrix", projectId, ids.join(",")],
    queryFn: () =>
      evidenceApi.matrix(projectId as number, { file_ids: ids }),
    enabled,
  });

  if (!enabled) return null;

  if (q.isLoading) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-border px-3 py-4 text-[13px] text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Building side-by-side…
      </div>
    );
  }

  if (q.isError || !q.data) {
    return (
      <p className="text-[13px] text-muted-foreground">
        Could not load matrix for comparison.{" "}
        <Link to="/research/compare?tab=extract" className="text-primary hover:underline">
          Extract evidence
        </Link>{" "}
        first.
      </p>
    );
  }

  const byId = new Map<number, MatrixRow>();
  for (const row of q.data.rows) byId.set(row.file_id, row);

  const columns = ids.map((id) => {
    const file = files.find((f) => f.id === id);
    const row = byId.get(id);
    return {
      id,
      title: row?.paper_title || file?.title || file?.name || `Paper ${id}`,
      year: row?.paper_year || file?.year || "",
      row,
    };
  });

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-card">
      <p className="border-b border-border px-3 py-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Side-by-side · Evidence Matrix
      </p>
      <table className="w-full min-w-[36rem] border-collapse text-left">
        <thead>
          <tr className="border-b border-border bg-muted/30">
            <th className="w-28 px-3 py-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Dimension
            </th>
            {columns.map((c) => (
              <th key={c.id} className="px-3 py-2 align-bottom">
                <Link
                  to={`/papers/${c.id}`}
                  className="line-clamp-2 text-[13px] font-semibold text-foreground hover:text-primary hover:underline"
                >
                  {c.title}
                </Link>
                {c.year ? (
                  <p className="mt-0.5 text-[11px] text-muted-foreground">{c.year}</p>
                ) : null}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {DIMENSIONS.map((dim) => (
            <tr key={dim.key} className="border-b border-border/70 last:border-0 align-top">
              <td className="px-3 py-2.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                {dim.label}
              </td>
              {columns.map((c) => {
                const cell = c.row?.[dim.key];
                const { text, missing } = cellText(cell);
                return (
                  <td
                    key={c.id}
                    className={cn(
                      "max-w-[18rem] px-3 py-2.5 text-[13px] leading-relaxed",
                      missing
                        ? "bg-amber-500/[0.04] text-amber-800/90 dark:text-amber-400/90"
                        : "text-foreground/90",
                    )}
                  >
                    {missing ? (
                      <Link
                        to="/research/compare?tab=extract"
                        className="font-medium hover:underline"
                      >
                        {text}
                      </Link>
                    ) : (
                      text
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
