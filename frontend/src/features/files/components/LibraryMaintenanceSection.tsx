/**
 * Library maintenance — duplicates + blockers, collapsed by default.
 * Not part of the reading desk hierarchy.
 */
import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LibraryAttentionRow } from "../libraryListViewModel";
import { paperTitle } from "../libraryListViewModel";
import { LibraryDuplicatesPanel } from "./LibraryDuplicatesPanel";

export function LibraryMaintenanceSection({
  projectId,
  attentionRows,
  attentionTotal,
  onOpenAttention,
  onShowAllNeedsPdf,
}: {
  projectId?: number | null;
  attentionRows: LibraryAttentionRow[];
  attentionTotal: number;
  onOpenAttention: (row: LibraryAttentionRow) => void;
  onShowAllNeedsPdf?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const hasAttention = attentionRows.length > 0;

  return (
    <section aria-label="Library maintenance" className="pt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 py-2 text-left text-[12px] text-text-tertiary transition-colors hover:text-text-secondary"
      >
        <ChevronDown
          className={cn(
            "size-3.5 shrink-0 transition-transform duration-200",
            open && "rotate-180",
          )}
        />
        <span className="font-medium uppercase tracking-[0.08em]">Maintenance</span>
        {hasAttention ? (
          <span className="normal-case tracking-normal text-text-tertiary">
            · {attentionTotal} need
            {attentionTotal === 1 ? "s" : ""} attention
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="space-y-4 border-t border-border/60 pt-3">
          {hasAttention ? (
            <div className="space-y-1.5">
              <p className="text-[12px] text-text-secondary">Needs attention</p>
              <ul className="divide-y divide-border border-y border-border">
                {attentionRows.map((row) => (
                  <li key={row.file.id}>
                    <button
                      type="button"
                      onClick={() => onOpenAttention(row)}
                      className="group flex w-full items-center gap-3 px-1 py-2.5 text-left transition-colors hover:bg-muted/25"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[13px] font-medium text-text-primary">
                          {paperTitle(row.file)}
                        </p>
                        <p className="text-[12px] text-text-secondary">{row.label}</p>
                      </div>
                      <span className="text-[12px] text-text-tertiary group-hover:text-text-secondary">
                        {row.actionLabel}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              {attentionTotal > attentionRows.length && onShowAllNeedsPdf ? (
                <button
                  type="button"
                  onClick={onShowAllNeedsPdf}
                  className="text-[12px] text-text-secondary transition-colors hover:text-text-accent"
                >
                  Show all needing attention ({attentionTotal})
                </button>
              ) : null}
            </div>
          ) : null}
          <LibraryDuplicatesPanel projectId={projectId} />
        </div>
      ) : null}
    </section>
  );
}
