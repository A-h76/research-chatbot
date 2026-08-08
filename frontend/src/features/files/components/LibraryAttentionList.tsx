/**
 * Quiet Needs attention rows — actionable blockers only.
 */
import { ChevronRight } from "lucide-react";
import type { LibraryAttentionRow } from "../libraryListViewModel";
import { paperTitle } from "../libraryListViewModel";

export function LibraryAttentionList({
  rows,
  total,
  onOpen,
  onShowAllNeedsPdf,
}: {
  rows: LibraryAttentionRow[];
  total: number;
  onOpen: (row: LibraryAttentionRow) => void;
  onShowAllNeedsPdf?: () => void;
}) {
  if (rows.length === 0) return null;

  return (
    <section aria-label="Needs attention" className="space-y-1.5">
      <p className="text-[12px] font-medium uppercase tracking-[0.08em] text-text-tertiary">
        Needs attention
      </p>
      <ul className="divide-y divide-border border-y border-border">
        {rows.map((row) => (
          <li key={row.file.id}>
            <button
              type="button"
              onClick={() => onOpen(row)}
              className="group flex w-full items-center gap-3 px-1 py-2.5 text-left transition-colors hover:bg-muted/25"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-medium text-text-primary">
                  {paperTitle(row.file)}
                </p>
                <p className="text-[12px] text-text-secondary">{row.label}</p>
              </div>
              <span className="inline-flex items-center gap-0.5 text-[12px] text-text-tertiary group-hover:text-text-secondary">
                {row.actionLabel}
                <ChevronRight className="size-3.5" />
              </span>
            </button>
          </li>
        ))}
      </ul>
      {total > rows.length && onShowAllNeedsPdf ? (
        <button
          type="button"
          onClick={onShowAllNeedsPdf}
          className="text-[12px] text-text-secondary transition-colors hover:text-text-accent"
        >
          Show all needing attention ({total})
        </button>
      ) : null}
    </section>
  );
}
