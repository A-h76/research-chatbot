/**
 * Quiet activity feed of researcher decisions (Phase A.2).
 * Product labels only — no "ResearchDecision" / analytics / graphs.
 */
import { useQuery } from "@tanstack/react-query";
import { evidenceApi, type ResearchDecisionDTO } from "../api";
import { cn } from "@/lib/utils";

function iconFor(type: string): string {
  switch (type) {
    case "ACCEPT":
      return "✓";
    case "REJECT":
      return "✗";
    case "IMPORTANT":
      return "★";
    case "OPEN_QUESTION":
      return "?";
    case "CONTRADICT":
      return "⚠";
    case "SUPPORT":
      return "+";
    default:
      return "·";
  }
}

function formatTime(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch {
    return "";
  }
}

function DecisionRow({ d }: { d: ResearchDecisionDTO }) {
  return (
    <li className="border-b border-border/60 py-2 last:border-0">
      <div className="flex items-start gap-2">
        <span
          className={cn(
            "mt-0.5 w-4 shrink-0 text-center text-[12px]",
            d.type === "ACCEPT" && "text-emerald-700 dark:text-emerald-300",
            d.type === "REJECT" && "text-muted-foreground",
            d.type === "IMPORTANT" && "text-amber-700 dark:text-amber-300",
            d.type === "OPEN_QUESTION" && "text-sky-700 dark:text-sky-300",
            d.type === "CONTRADICT" && "text-amber-800 dark:text-amber-200",
          )}
          aria-hidden
        >
          {iconFor(d.type)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-medium text-foreground">{d.label}</p>
          {d.claim_preview ? (
            <p className="mt-0.5 line-clamp-2 text-[11px] text-muted-foreground">
              “{d.claim_preview}”
            </p>
          ) : null}
          {d.reason ? (
            <p className="mt-0.5 text-[10px] text-muted-foreground">Why: {d.reason}</p>
          ) : null}
          <p className="mt-0.5 text-[10px] tabular-nums text-muted-foreground/80">
            {formatTime(d.timestamp)}
          </p>
        </div>
      </div>
    </li>
  );
}

export function DecisionActivityFeed({ projectId }: { projectId: number | null | undefined }) {
  const q = useQuery({
    queryKey: ["research-decisions", projectId],
    queryFn: () => evidenceApi.listDecisions(projectId as number, 30),
    enabled: projectId != null,
    refetchInterval: 15_000,
  });

  const items = q.data?.items ?? [];

  return (
    <section className="rounded-md border border-border bg-card/40 p-2.5" aria-label="Today’s decisions">
      <h3 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Decisions
      </h3>
      <p className="mt-0.5 text-[10px] text-muted-foreground">
        What you’ve accepted, rejected, or marked — remembered for this project.
      </p>
      {q.isLoading ? (
        <p className="mt-2 text-[11px] text-muted-foreground">Loading…</p>
      ) : items.length === 0 ? (
        <p className="mt-2 text-[11px] text-muted-foreground">
          No decisions yet. Accept or reject evidence to start the project’s memory.
        </p>
      ) : (
        <ul className="mt-2 max-h-56 overflow-auto">
          {items.map((d) => (
            <DecisionRow key={d.id} d={d} />
          ))}
        </ul>
      )}
    </section>
  );
}
