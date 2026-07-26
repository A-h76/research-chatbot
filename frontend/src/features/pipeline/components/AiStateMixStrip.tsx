import { AiStateBadge, type AiStateResolved } from "./AiStateBadge";
import { AI_STATE_LABELS, type AiStateId } from "../aiState";

const MIX_ORDER: AiStateId[] = [
  "chat_ready",
  "graph_ready",
  "evidence_ready",
  "classifying",
  "understanding",
  "queued",
  "uploading",
  "needs_attention",
];

/**
 * Project Overview mix strip — counts per headline AI state (DESIGN-SYSTEM §12.2).
 */
export function AiStateMixStrip({
  states,
}: {
  states: AiStateResolved[];
}) {
  const counts = new Map<AiStateId, number>();
  for (const s of states) {
    counts.set(s.id, (counts.get(s.id) ?? 0) + 1);
  }

  const parts = MIX_ORDER.filter((id) => (counts.get(id) ?? 0) > 0).map((id) => ({
    id,
    count: counts.get(id)!,
    label: AI_STATE_LABELS[id],
  }));

  if (parts.length === 0) return null;

  return (
    <div
      className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs"
      aria-label="Pipeline mix"
    >
      {parts.map((p) => (
        <span key={p.id} className="inline-flex items-center gap-1.5">
          <AiStateBadge state={{ id: p.id, label: p.label }} />
          <span className="tabular-nums text-muted-foreground">{p.count}</span>
        </span>
      ))}
    </div>
  );
}
