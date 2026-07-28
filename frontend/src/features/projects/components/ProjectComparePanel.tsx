import { useMemo } from "react";
import { CompareGapsWorkbench } from "@/features/analysis/components/CompareGapsWorkbench";
import { useFiles } from "@/features/files/useFiles";
import { Skeleton } from "@/components/ui/skeleton";

/** In-workspace compare & gaps scoped to project papers. */
export function ProjectComparePanel({ projectId }: { projectId: number }) {
  const { data, isLoading } = useFiles({
    project_id: projectId,
    kind: "document",
    limit: 500,
  });

  const ready = useMemo(
    () => (data?.items ?? []).filter((f) => f.meta_status === "done"),
    [data?.items],
  );

  if (isLoading) {
    return <Skeleton className="h-48 w-full rounded-xl" />;
  }

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-sm font-semibold">Compare &amp; gaps</h2>
        <p className="text-xs text-muted-foreground">
          Cross-paper analysis on papers in this project ({ready.length} ready).
        </p>
      </div>
      <CompareGapsWorkbench
        files={ready}
        projectId={projectId}
        emptyTitle="No analysed papers in this project"
        emptyDescription="Upload papers and wait for analysis to complete, then compare them here."
      />
    </div>
  );
}
