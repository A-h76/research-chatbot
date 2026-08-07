import { cn } from "@/lib/utils";
import type { PaperTabId } from "../tabs";

type Signal = {
  key: string;
  label: string;
  value: string;
  tab: PaperTabId;
};

/**
 * Compact scientific status strip — reading stays the hero, not a dashboard.
 */
export function PaperStatStrip({
  evidenceLabel,
  entityCount,
  entitySkipped,
  graphNodes,
  graphEdges,
  classificationLabel,
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
      label: "Quality",
      value: evidenceLabel ?? "Not assessed",
      tab: "evidence",
    },
    {
      key: "entities",
      label: "Entities",
      value: entitySkipped
        ? "Skipped"
        : entityCount != null
          ? String(entityCount)
          : "—",
      tab: "entities",
    },
    {
      key: "graph",
      label: "Links",
      value:
        graphNodes != null
          ? `${graphEdges ?? 0} edges`
          : "—",
      tab: "graph",
    },
    {
      key: "classification",
      label: "Profile",
      value: classificationLabel ?? "—",
      tab: "classification",
    },
  ];

  return (
    <div
      role="group"
      aria-label="Scientific signals"
      className={cn(
        "flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] text-muted-foreground",
        className,
      )}
    >
      {signals.map((s, i) => (
        <span key={s.key} className="inline-flex items-center gap-2">
          {i > 0 ? (
            <span className="text-border" aria-hidden>
              ·
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => onJump(s.tab)}
            className="inline-flex items-baseline gap-1.5 rounded-sm transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <span className="font-medium text-muted-foreground/80">{s.label}</span>
            <span className="tabular-nums text-foreground/90">{s.value}</span>
          </button>
        </span>
      ))}
    </div>
  );
}
