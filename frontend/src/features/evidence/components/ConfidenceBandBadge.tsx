/**
 * Confidence Doctrine — confidence must be visible (Design Language v1 §2b).
 * Semantic color only; never used as page chrome.
 */
import { cn } from "@/lib/utils";
import type { ConfidenceBand } from "../types";

const BAND_COPY: Record<ConfidenceBand, string> = {
  high: "High confidence",
  moderate: "Moderate confidence",
  low: "Low confidence",
};

export function ConfidenceBandBadge({
  band,
  className,
  compact,
}: {
  band: ConfidenceBand | string | null | undefined;
  className?: string;
  /** Omit “confidence” word for dense inspector chips */
  compact?: boolean;
}) {
  const normalized = (band || "").toLowerCase() as ConfidenceBand;
  const known = normalized === "high" || normalized === "moderate" || normalized === "low";
  const label = known
    ? compact
      ? normalized
      : BAND_COPY[normalized]
    : band
      ? String(band)
      : "Unknown confidence";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide",
        known &&
          normalized === "high" &&
          "border-sem-ready/35 bg-sem-ready/10 text-sem-ready",
        known &&
          normalized === "moderate" &&
          "border-sem-warn/35 bg-sem-warn/10 text-sem-warn",
        known &&
          normalized === "low" &&
          "border-sem-error/35 bg-sem-error/10 text-sem-error",
        !known && "border-border bg-muted/40 text-muted-foreground",
        className,
      )}
      title={known ? BAND_COPY[normalized] : label}
      aria-label={known ? BAND_COPY[normalized] : label}
    >
      <span
        aria-hidden
        className={cn(
          "size-1.5 shrink-0 rounded-full",
          known && normalized === "high" && "bg-sem-ready",
          known && normalized === "moderate" && "bg-sem-warn",
          known && normalized === "low" && "bg-sem-error",
          !known && "bg-muted-foreground/50",
        )}
      />
      {label}
    </span>
  );
}
