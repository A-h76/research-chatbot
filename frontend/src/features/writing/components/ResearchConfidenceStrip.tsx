/**
 * Research Confidence — decision metrics only (not AI vanity scores).
 */
import { cn } from "@/lib/utils";
import type { WritingMetrics, WritingReview } from "@/features/evidence/hooks/useGroundedWriting";

type Props = {
  metrics?: WritingMetrics | null;
  review?: WritingReview | null;
  className?: string;
};

export function ResearchConfidenceStrip({ metrics, review, className }: Props) {
  const coverage =
    metrics?.citation_coverage != null
      ? Math.round(metrics.citation_coverage * 100)
      : metrics?.grounding_pct != null
        ? Math.round(metrics.grounding_pct * 100)
        : null;
  const grounding =
    metrics?.grounding_pct != null ? Math.round(metrics.grounding_pct * 100) : null;
  const unsupported = metrics?.unsupported_claims ?? null;
  const reviewerStatus = review?.status ?? metrics?.reviewer_status ?? null;

  const empty = coverage == null && grounding == null && unsupported == null && !reviewerStatus;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border border-border bg-card px-3 py-2",
        className,
      )}
      role="region"
      aria-label="Research Confidence"
    >
      <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Research Confidence
      </span>
      {empty ? (
        <span className="text-[12px] text-muted-foreground">
          Generate from evidence to see coverage, reviewer, and unsupported claims
        </span>
      ) : (
        <>
          {coverage != null && (
            <Metric label="Evidence coverage" value={`${coverage}%`} />
          )}
          {grounding != null && coverage == null && (
            <Metric label="Grounding" value={`${grounding}%`} />
          )}
          {reviewerStatus != null && (
            <Metric
              label="Research Reviewer"
              value={String(reviewerStatus).toLowerCase() === "pass" ? "Passed" : "Needs review"}
              tone={String(reviewerStatus).toLowerCase() === "pass" ? "ok" : "warn"}
            />
          )}
          {unsupported != null && (
            <Metric
              label="Unsupported"
              value={String(unsupported)}
              tone={unsupported === 0 ? "ok" : "warn"}
            />
          )}
        </>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "ok" | "warn";
}) {
  return (
    <span className="inline-flex items-baseline gap-1.5 text-[12px]">
      <span className="text-muted-foreground">{label}</span>
      <span
        className={cn(
          "font-medium tabular-nums",
          tone === "ok" && "text-emerald-700 dark:text-emerald-300",
          tone === "warn" && "text-amber-700 dark:text-amber-300",
          !tone && "text-foreground",
        )}
      >
        {value}
      </span>
    </span>
  );
}
