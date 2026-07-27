import { PAPER_TAB_LABELS, type PaperTabId } from "../tabs";

/** Placeholder for M5–M7 panels — no fake data. */
export function PaperTabPlaceholder({ tab }: { tab: PaperTabId }) {
  const label = PAPER_TAB_LABELS[tab];
  return (
    <div className="rounded-xl border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
      <p className="text-sm font-medium text-foreground">{label}</p>
      <p className="mt-2 text-sm text-muted-foreground">
        Coming in the next milestone.
      </p>
    </div>
  );
}
