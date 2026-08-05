import { PipelineStepper } from "./PipelineStepper";
import { resolveAiState } from "../aiState";
import { isPipelineProcessing } from "../isPipelineProcessing";
import type { PipelineDerived } from "../types";
import { useState } from "react";
import { Check, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

function formatProcessedAgo(iso: string | null | undefined): string | null {
  if (!iso) return null;
  // Naive API timestamps are UTC — treat as such so UTC+N locales don't show N hours ago.
  const normalized =
    /(?:Z|[+-]\d{2}:?\d{2})$/i.test(iso.trim()) ? iso.trim() : `${iso.trim().replace(/ /, "T")}Z`;
  const t = Date.parse(normalized);
  if (Number.isNaN(t)) return null;
  const mins = Math.max(0, Math.round((Date.now() - t) / 60_000));
  if (mins < 1) return "just now";
  if (mins === 1) return "1 minute ago";
  if (mins < 60) return `${mins} minutes ago`;
  const hrs = Math.round(mins / 60);
  if (hrs === 1) return "1 hour ago";
  if (hrs < 48) return `${hrs} hours ago`;
  const days = Math.round(hrs / 24);
  return days === 1 ? "1 day ago" : `${days} days ago`;
}

/**
 * D3 — Pipeline feedback.
 * Processing/error: full stepper (above tabs).
 * Ready: one collapsed line — details on demand.
 */
export function PipelineStatusPanel({
  derived,
  metaStatus,
  updatedAt,
  className,
  /** Force compact chrome (e.g. Paper Chat header strip). */
  compact,
}: {
  derived: PipelineDerived;
  metaStatus?: string | null;
  updatedAt?: string | null;
  className?: string;
  compact?: boolean;
}) {
  const processing = isPipelineProcessing(derived, metaStatus);
  const showExpandedByDefault = processing || derived.isError;
  const [open, setOpen] = useState(false);

  const expanded = showExpandedByDefault ? true : open;
  const headline = resolveAiState({ derived, metaStatus });
  const ago = formatProcessedAgo(updatedAt);

  if (showExpandedByDefault) {
    return (
      <section
        aria-label="Pipeline progress"
        className={cn(
          "rounded-lg border border-border bg-card",
          compact ? "px-3 py-2.5" : "px-3 py-3.5 sm:px-4",
          className,
        )}
      >
        {!compact && (
          <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Pipeline
          </p>
        )}
        {compact && (
          <p className="mb-2 text-[12px] font-medium text-foreground">
            {headline.label}
            {derived.isError ? " — needs attention" : "…"}
          </p>
        )}
        <PipelineStepper derived={derived} metaStatus={metaStatus} />
        {derived.isError && derived.errors.length > 0 && (
          <p className="mt-2 text-xs text-sem-error" role="alert">
            {derived.errors[0]}
          </p>
        )}
      </section>
    );
  }

  return (
    <section
      aria-label="Pipeline status"
      className={cn("rounded-lg border border-border bg-card/50", className)}
    >
      <button
        type="button"
        className="flex w-full items-center gap-2 px-3 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset rounded-lg sm:px-3.5"
        aria-expanded={expanded}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-sem-ready/15 text-sem-ready">
          <Check className="size-3" strokeWidth={3} aria-hidden />
        </span>
        <span className="min-w-0 flex-1 text-[13px] text-foreground">
          <span className="font-medium">{headline.label}</span>
          {ago && (
            <span className="text-muted-foreground"> · Processed {ago}</span>
          )}
          <span className="text-muted-foreground">
            {" · "}
            {expanded ? "Hide details" : "View details"}
          </span>
        </span>
        {expanded ? (
          <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
        ) : (
          <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
        )}
      </button>
      {expanded && (
        <div className="border-t border-border px-3 py-3 sm:px-3.5">
          <PipelineStepper derived={derived} metaStatus={metaStatus} />
          {derived.warnings.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs text-muted-foreground" role="list">
              {derived.warnings.slice(0, 3).map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

/** @deprecated Prefer PipelineStatusPanel */
export const PipelineStatusCard = PipelineStatusPanel;
