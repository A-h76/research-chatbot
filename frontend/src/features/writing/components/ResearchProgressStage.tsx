/**
 * Sequential research-stage progress (UI_UX_VISION_BETA_v1.0).
 * Never say Thinking / Generating / Loading.
 */
import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export const LIT_REVIEW_STAGES = [
  "Planning literature review",
  "Organising evidence",
  "Writing literature review",
  "Linking citations",
  "Verifying evidence",
] as const;

type Props = {
  active?: boolean;
  stages?: readonly string[];
  /** Optional live metric while work is in progress */
  liveMetric?: string | null;
  className?: string;
};

export function ResearchProgressStage({
  active = true,
  stages = LIT_REVIEW_STAGES,
  liveMetric = null,
  className,
}: Props) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!active) {
      setIndex(0);
      return;
    }
    setIndex(0);
    const id = window.setInterval(() => {
      setIndex((i) => (i < stages.length - 1 ? i + 1 : i));
    }, 2200);
    return () => window.clearInterval(id);
  }, [active, stages.length]);

  if (!active) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={cn(
        "rounded-lg border border-border bg-muted/30 px-4 py-3",
        className,
      )}
    >
      <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Research progress
      </p>
      <ul className="space-y-1.5">
        {stages.map((label, i) => {
          const done = i < index;
          const current = i === index;
          return (
            <li
              key={label}
              className={cn(
                "flex items-center gap-2 text-[13px] transition-opacity",
                done && "text-muted-foreground",
                current && "font-medium text-foreground",
                !done && !current && "opacity-40 text-muted-foreground",
              )}
            >
              {done ? (
                <Check className="size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden />
              ) : current ? (
                <span
                  className="size-3.5 shrink-0 animate-pulse rounded-full bg-primary"
                  aria-hidden
                />
              ) : (
                <span className="size-3.5 shrink-0 rounded-full border border-border" aria-hidden />
              )}
              <span>{label}{current ? "…" : done ? "" : ""}</span>
            </li>
          );
        })}
      </ul>
      {liveMetric ? (
        <p className="mt-2 text-[11px] tabular-nums text-muted-foreground">{liveMetric}</p>
      ) : null}
    </div>
  );
}
