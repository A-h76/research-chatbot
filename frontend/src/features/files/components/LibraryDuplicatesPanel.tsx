import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { libraryBridgeApi } from "../libraryBridgeApi";
import { toast } from "@/components/common/Toast";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { queryKeys } from "@/lib/queryKeys";

type DupGroup = {
  reason: string;
  key: string;
  keep_id: number;
  file_ids: number[];
  titles: string[];
  has_pdf: boolean[];
};

export function LibraryDuplicatesPanel({
  projectId,
}: {
  projectId?: number | null;
}) {
  const qc = useQueryClient();
  const [pending, setPending] = useState<DupGroup | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["library", "duplicates", projectId ?? "all"],
    queryFn: () => libraryBridgeApi.duplicates(projectId),
    staleTime: 60_000,
  });

  const merge = useMutation({
    mutationFn: (g: DupGroup) =>
      libraryBridgeApi.mergeDuplicates({
        keep_id: g.keep_id,
        merge_ids: g.file_ids.filter((id) => id !== g.keep_id),
      }),
    onSuccess: (res) => {
      toast.success(`Merged ${res.merged_ids?.length ?? 0} duplicate(s)`);
      setPending(null);
      void qc.invalidateQueries({ queryKey: ["library"] });
      void qc.invalidateQueries({ queryKey: queryKeys.files });
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : "Merge failed");
    },
  });

  const items = data?.items ?? [];
  if (isLoading || items.length === 0) return null;

  return (
    <div className="rounded-lg border border-border px-3 py-2.5">
      <p className="text-[13px] font-medium">
        Possible duplicates
        <span className="ml-2 font-normal text-muted-foreground">
          {items.length} group{items.length === 1 ? "" : "s"}
        </span>
      </p>
      <ul className="mt-2 max-h-48 space-y-2 overflow-y-auto">
        {items.slice(0, 8).map((g) => (
          <li
            key={`${g.reason}-${g.key}-${g.keep_id}`}
            className="flex items-start justify-between gap-2 border-b border-border/60 pb-2 last:border-0 last:pb-0"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12px] font-medium" title={g.titles[0]}>
                {g.titles[0] || "Untitled"}
              </p>
              <p className="text-[11px] text-muted-foreground">
                {g.file_ids.length} copies · {g.reason.replace("_", " ")}
                {g.has_pdf.some(Boolean) ? " · PDF present" : " · metadata only"}
              </p>
            </div>
            <button
              type="button"
              disabled={merge.isPending}
              onClick={() => setPending(g)}
              className="shrink-0 rounded border border-border px-2 py-0.5 text-[11px] text-muted-foreground hover:text-foreground disabled:opacity-50"
            >
              Merge
            </button>
          </li>
        ))}
      </ul>

      <ConfirmDialog
        open={pending != null}
        onOpenChange={(o) => {
          if (!o) setPending(null);
        }}
        title="Merge duplicates?"
        description={
          pending
            ? `Keep “${pending.titles[0] || "Untitled"}” and merge ${
                pending.file_ids.length - 1
              } other cop${pending.file_ids.length - 1 === 1 ? "y" : "ies"}. Metadata fills gaps; the PDF-bearing record is preferred.`
            : ""
        }
        confirmLabel="Merge"
        onConfirm={() => {
          if (pending) merge.mutate(pending);
        }}
      />
    </div>
  );
}
