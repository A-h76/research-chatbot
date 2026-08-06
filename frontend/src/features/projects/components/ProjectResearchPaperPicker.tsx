import { FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { UserFile } from "@/types/api";
import { isCrossPaperResearchReady } from "../crossPaperResearchReady";

const MAX_SELECTED = 10;

export function ProjectResearchPaperPicker({
  papers,
  selectedIds,
  onSelectedIdsChange,
}: {
  papers: UserFile[];
  selectedIds: number[];
  onSelectedIdsChange: (ids: number[]) => void;
}) {
  const ready = papers.filter(isCrossPaperResearchReady);
  const pending = papers.filter((f) => !isCrossPaperResearchReady(f));
  const selectedSet = new Set(selectedIds);

  function toggle(id: number) {
    if (selectedSet.has(id)) {
      onSelectedIdsChange(selectedIds.filter((x) => x !== id));
      return;
    }
    if (selectedIds.length >= MAX_SELECTED) return;
    onSelectedIdsChange([...selectedIds, id]);
  }

  function selectAllReady() {
    onSelectedIdsChange(ready.slice(0, MAX_SELECTED).map((f) => f.id));
  }

  function clearSelection() {
    onSelectedIdsChange([]);
  }

  return (
    <section className="space-y-2 rounded-xl border border-border px-3 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Papers in this run ({selectedIds.length} selected)
          </h3>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Pick 2–{MAX_SELECTED} analysis-ready papers. Cross-paper presets compare your selection.
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={selectAllReady}>
            Select all ready
          </Button>
          {selectedIds.length > 0 && (
            <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={clearSelection}>
              Clear
            </Button>
          )}
        </div>
      </div>

      <ul className="space-y-1 max-h-48 overflow-y-auto scrollbar-thin">
        {ready.map((f) => {
          const checked = selectedSet.has(f.id);
          const atCap = !checked && selectedIds.length >= MAX_SELECTED;
          const title = f.title || f.name;
          return (
            <li key={f.id}>
              <label
                className={cn(
                  "flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors",
                  checked ? "bg-accent-soft/60" : "hover:bg-muted/40",
                  atCap && "cursor-not-allowed opacity-50",
                )}
              >
                <input
                  type="checkbox"
                  className="size-3.5 shrink-0 accent-primary"
                  checked={checked}
                  disabled={atCap}
                  onChange={() => toggle(f.id)}
                />
                <FileText className="size-3.5 shrink-0 text-primary" />
                <span className="min-w-0 flex-1 truncate">{title}</span>
                <span className="shrink-0 text-[10px] text-emerald-700 dark:text-emerald-400">
                  Ready
                </span>
              </label>
            </li>
          );
        })}
      </ul>

      {pending.length > 0 && (
        <div className="border-t border-border pt-2 space-y-1">
          <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Still analysing ({pending.length})
          </p>
          <ul className="space-y-0.5">
            {pending.map((f) => (
              <li
                key={f.id}
                className="flex items-center gap-2 px-2 py-1 text-xs text-muted-foreground"
              >
                <FileText className="size-3 shrink-0 opacity-50" />
                <span className="min-w-0 flex-1 truncate">{f.title || f.name}</span>
                <span className="shrink-0 text-[10px] capitalize">
                  {f.paper_analysis_status === "running" ? "Analysing" : "Waiting"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {selectedIds.length > 0 && selectedIds.length < 2 && (
        <p className="text-[11px] text-amber-700 dark:text-amber-400">
          Select at least 2 papers to run cross-paper research.
        </p>
      )}
    </section>
  );
}

export { MAX_SELECTED as MAX_RESEARCH_PAPERS };
