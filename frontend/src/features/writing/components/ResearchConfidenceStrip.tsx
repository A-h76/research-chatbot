/**
 * Research Confidence — decision metrics + Bklit coverage ring.
 */
import { cn } from "@/lib/utils";
import { Ring } from "@/components/charts/ring";
import { RingCenter } from "@/components/charts/ring-center";
import { RingChart } from "@/components/charts/ring-chart";
import type { WritingMetrics, WritingReview } from "@/features/evidence/hooks/useGroundedWriting";

type Props = {
  metrics?: WritingMetrics | null;
  review?: WritingReview | null;
  reviewerVersion?: string | null;
  className?: string;
};

export function ResearchConfidenceStrip({
  metrics,
  review,
  reviewerVersion,
  className,
}: Props) {
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
  const versionLabel = reviewerVersion || review?.reviewer_version || null;

  const empty = coverage == null && grounding == null && unsupported == null && !reviewerStatus;
  const ringValue = coverage ?? grounding;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-4 gap-y-2 rounded-md border border-border bg-card px-3 py-2",
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
          {ringValue != null && (
            <div className="flex items-center gap-3">
              <div className="size-[72px] shrink-0">
                <RingChart
                  data={[
                    {
                      label: coverage != null ? "Coverage" : "Grounding",
                      value: ringValue,
                      maxValue: 100,
                      color: "var(--primary)",
                    },
                  ]}
                  size={72}
                  strokeWidth={8}
                  ringGap={4}
                  baseInnerRadius={20}
                  animationDuration={700}
                >
                  <Ring index={0} showGlow={false} />
                  <RingCenter
                    suffix="%"
                    defaultLabel={coverage != null ? "Coverage" : "Grounding"}
                  />
                </RingChart>
              </div>
              <div className="flex flex-col gap-1">
                {coverage != null && grounding != null && coverage !== grounding && (
                  <Metric label="Grounding" value={`${grounding}%`} />
                )}
                {reviewerStatus != null && (
                  <Metric
                    label="Research Reviewer"
                    value={
                      String(reviewerStatus).toLowerCase() === "pass"
                        ? versionLabel
                          ? `Passed · v${versionLabel}`
                          : "Passed"
                        : versionLabel
                          ? `Needs review · v${versionLabel}`
                          : "Needs review"
                    }
                    tone={
                      String(reviewerStatus).toLowerCase() === "pass" ? "ok" : "warn"
                    }
                  />
                )}
                {unsupported != null && (
                  <Metric
                    label="Unsupported"
                    value={String(unsupported)}
                    tone={unsupported === 0 ? "ok" : "warn"}
                  />
                )}
              </div>
            </div>
          )}
          {ringValue == null && (
            <>
              {reviewerStatus != null && (
                <Metric
                  label="Research Reviewer"
                  value={
                    String(reviewerStatus).toLowerCase() === "pass"
                      ? versionLabel
                        ? `Passed · v${versionLabel}`
                        : "Passed"
                      : versionLabel
                        ? `Needs review · v${versionLabel}`
                        : "Needs review"
                  }
                  tone={
                    String(reviewerStatus).toLowerCase() === "pass" ? "ok" : "warn"
                  }
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
