import { cn } from "@/lib/utils";
import type { PaperTabId } from "../tabs";

type Signal = {
  key: string;
  label: string;
  value: string;
  hint: string;
  tab: PaperTabId;
};

/**
 * D4 — Scientific StatStrip. Jumps to workspace tabs; not decorative cards.
 */
export function PaperStatStrip({
  evidenceLabel,
  evidenceHint,
  entityCount,
  entitySkipped,
  graphNodes,
  graphEdges,
  classificationLabel,
  classificationHint,
  onJump,
  className,
}: {
  evidenceLabel?: string | null;
  evidenceHint?: string | null;
  entityCount?: number | null;
  entitySkipped?: boolean;
  graphNodes?: number | null;
  graphEdges?: number | null;
  classificationLabel?: string | null;
  classificationHint?: string | null;
  onJump: (tab: PaperTabId) => void;
  className?: string;
}) {
  const signals: Signal[] = [
    {
      key: "evidence",
      label: "Evidence quality",
      value: evidenceLabel ?? "—",
      hint: evidenceHint ?? "Open Evidence",
      tab: "evidence",
    },
    {
      key: "entities",
      label: "Knowledge coverage",
      value: entitySkipped ? "Skipped" : entityCount != null ? String(entityCount) : "—",
      hint: entitySkipped ? "Not extracted" : "entities extracted",
      tab: "entities",
    },
    {
      key: "graph",
      label: "Relationship network",
      value: graphNodes != null ? String(graphNodes) : "—",
      hint:
        graphNodes != null
          ? `${graphEdges ?? 0} connected edges`
          : "Open Graph",
      tab: "graph",
    },
    {
      key: "classification",
      label: "Profile",
      value: classificationLabel ?? "—",
      hint: classificationHint ?? "Open Research Profile",
      tab: "classification",
    },
  ];

  return (
    <section aria-label="Scientific signals" className={cn(className)}>
      <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Scientific signals
      </p>
      <div className="grid overflow-hidden rounded-lg border border-border bg-card sm:grid-cols-2 lg:grid-cols-4">
        {signals.map((s, i) => (
          <button
            key={s.key}
            type="button"
            onClick={() => onJump(s.tab)}
            className={cn(
              "p-3 text-left transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
              i < signals.length - 1 && "border-b border-border sm:border-b-0",
              i % 2 === 0 && "sm:border-r",
              i < 2 && "lg:border-b-0",
              i < 3 && "lg:border-r",
            )}
          >
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              {s.label}
            </p>
            <p className="mt-1 truncate text-[15px] font-semibold tabular-nums text-foreground">
              {s.value}
            </p>
            <p className="mt-0.5 truncate text-[12px] text-muted-foreground">{s.hint}</p>
          </button>
        ))}
      </div>
    </section>
  );
}
