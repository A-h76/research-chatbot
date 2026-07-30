/**
 * Sequential research-stage progress (UI_UX_VISION_BETA_v1.0).
 * One stage at a time — never Thinking / Generating / Loading.
 */
import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export const LIT_REVIEW_STAGES = [
  "Planning literature review",
  "Organising evidence",
  "Writing literature review",
  "Linking citations",
  "Verifying evidence",
] as const;

/** Evidence Extraction Pipeline stages (glossary: Extracting evidence). */
export const EXTRACT_EVIDENCE_STAGES = [
  "Preparing paper",
  "Extracting evidence",
  "Organising candidates",
  "Ready for review",
] as const;

type Props = {
  active?: boolean;
  stages?: readonly string[];
  /** Optional live metric while work is in progress */
  liveMetric?: string | null;
  /** When set, show completion instead of pulsing stages */
  doneLabel?: string | null;
  className?: string;
};

export function ResearchProgressStage({
  active = true,
  stages = LIT_REVIEW_STAGES,
  liveMetric = null,
  doneLabel = null,
  className,
}: Props) {
  const [index, setIndex] = useState(0);
  const reduceMotion = useReducedMotion();

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

  if (!active && !doneLabel) return null;

  if (doneLabel) {
    return (
      <div
        role="status"
        aria-live="polite"
        className={cn(
          "overflow-hidden rounded-lg border border-emerald-700/30 bg-emerald-500/5 px-4 py-3",
          className,
        )}
      >
        <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Research progress
        </p>
        <div className="flex items-center gap-2.5">
          <Check
            className="size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400"
            aria-hidden
          />
          <p className="text-[14px] font-medium tracking-tight text-foreground">{doneLabel}</p>
        </div>
      </div>
    );
  }

  const current = stages[index] ?? stages[0];

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={cn(
        "overflow-hidden rounded-lg border border-border bg-muted/30 px-4 py-3",
        className,
      )}
    >
      <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Research progress
      </p>

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={current}
          initial={reduceMotion ? false : { opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduceMotion ? undefined : { opacity: 0, y: -4 }}
          transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          className="flex items-center gap-2.5"
        >
          <span
            className="relative flex size-3.5 shrink-0 items-center justify-center"
            aria-hidden
          >
            <span className="absolute inset-0 rounded-full bg-primary/25" />
            <span className="size-2 animate-pulse rounded-full bg-primary" />
          </span>
          <p className="text-[14px] font-medium tracking-tight text-foreground">
            {current}…
          </p>
        </motion.div>
      </AnimatePresence>

      {index > 0 ? (
        <ul className="mt-2.5 space-y-1 border-t border-border/60 pt-2">
          {stages.slice(0, index).map((label) => (
            <li
              key={label}
              className="flex items-center gap-2 text-[12px] text-muted-foreground"
            >
              <Check
                className="size-3 shrink-0 text-emerald-600 dark:text-emerald-400"
                aria-hidden
              />
              <span>{label}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {liveMetric ? (
        <p className="mt-2 text-[11px] tabular-nums text-muted-foreground">{liveMetric}</p>
      ) : null}
    </div>
  );
}
