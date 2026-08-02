/**
 * Research Reviewer panel (EPIC-0005 B-511–B-513).
 * Loads persisted reviewer-runs when available; falls back to in-memory writing.review.
 */
import { useEffect, useMemo, useState } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { evidenceApi } from "@/features/evidence/api";
import type { WritingReview } from "@/features/evidence/hooks/useGroundedWriting";
import type { ReviewerRunDTO } from "@/features/writing/types/reviewer";
import { cn } from "@/lib/utils";

type IssueRow = WritingReview["issues"][number];

const SEVERITY_ORDER = ["error", "warning", "info"] as const;

function groupBySeverity(issues: IssueRow[]): Record<string, IssueRow[]> {
  const out: Record<string, IssueRow[]> = { error: [], warning: [], info: [], other: [] };
  for (const issue of issues) {
    const sev = String(issue.severity || "warning").toLowerCase();
    if (sev === "error" || sev === "warning" || sev === "info") out[sev].push(issue);
    else out.other.push(issue);
  }
  return out;
}

export function ResearchReviewerPanel({
  documentId,
  liveReview,
  className,
  onFocusSection,
  refreshKey = 0,
}: {
  documentId: number | null;
  /** In-memory review from the last grounded generate (optional). */
  liveReview?: WritingReview | null;
  className?: string;
  onFocusSection?: (sectionId: string) => void;
  /** Bump after Accept / generate to refetch persisted run. */
  refreshKey?: number;
}) {
  const [run, setRun] = useState<ReviewerRunDTO | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "empty" | "error">("idle");

  useEffect(() => {
    if (documentId == null) {
      setRun(null);
      setStatus("idle");
      return;
    }
    let cancelled = false;
    setStatus("loading");
    evidenceApi
      .latestReviewerRun(documentId)
      .then((row) => {
        if (cancelled) return;
        setRun(row);
        setStatus("ok");
      })
      .catch(() => {
        if (cancelled) return;
        setRun(null);
        setStatus(liveReview ? "ok" : "empty");
      });
    return () => {
      cancelled = true;
    };
  }, [documentId, refreshKey, liveReview]);

  const review: WritingReview | null = useMemo(() => {
    if (run?.review) return run.review;
    return liveReview || null;
  }, [run, liveReview]);

  const reviewerVersion =
    review?.reviewer_version || run?.reviewer_version || liveReview?.reviewer_version || null;
  const issues = review?.issues || [];
  const grouped = groupBySeverity(issues);
  const errorCount = grouped.error.length;
  const grounding =
    review?.metrics?.grounding_pct != null
      ? Math.round(review.metrics.grounding_pct * 100)
      : run?.metrics && typeof run.metrics.grounding_pct === "number"
        ? Math.round(Number(run.metrics.grounding_pct) * 100)
        : null;
  const coverage =
    review?.metrics?.citation_coverage_pct != null
      ? Math.round(review.metrics.citation_coverage_pct * 100)
      : null;

  if (!review && status === "loading") {
    return (
      <p className={cn("text-[11px] text-muted-foreground", className)}>
        Loading Research Reviewer…
      </p>
    );
  }

  if (!review) {
    return (
      <div
        className={cn(
          "rounded-md border border-border bg-card/40 px-3 py-2 text-[11px] text-muted-foreground",
          className,
        )}
      >
        <p className="font-medium text-foreground/80">Research Reviewer</p>
        <p className="mt-0.5">No issues — generate a grounded draft to run the reviewer.</p>
      </div>
    );
  }

  return (
    <div
      className={cn("rounded-md border border-border bg-card/40 px-3 py-2", className)}
      role="region"
      aria-label="Research Reviewer"
    >
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-[11px] font-medium text-foreground">Research Reviewer</p>
        <p className="text-[10px] tabular-nums text-muted-foreground">
          {reviewerVersion ? `v${reviewerVersion}` : "version n/a"}
          {review.status ? ` · ${review.status}` : ""}
          {grounding != null ? ` · grounding ${grounding}%` : ""}
          {coverage != null ? ` · coverage ${coverage}%` : ""}
          {run?.id != null ? ` · run #${run.id}` : " · live"}
        </p>
      </div>

      {issues.length === 0 ? (
        <p className="text-[11px] text-emerald-800 dark:text-emerald-200">No issues</p>
      ) : (
        <Accordion className="border-t border-border pt-1">
          {SEVERITY_ORDER.map((sev) => {
            const rows = grouped[sev];
            if (!rows.length) return null;
            return (
              <AccordionItem key={sev} value={`sev-${sev}`}>
                <AccordionTrigger className="py-2 text-[12px]">
                  <span className="capitalize">{sev}</span>
                  <span className="ml-2 text-[11px] font-normal text-muted-foreground">
                    {rows.length}
                    {sev === "error" && errorCount > 0 ? " · blocks Accept/export" : ""}
                  </span>
                </AccordionTrigger>
                <AccordionContent className="pb-2">
                  <ul className="space-y-1.5 text-[11px] text-amber-800 dark:text-amber-200">
                    {rows.map((issue, idx) => {
                      const sid = issue.section_id;
                      const clickable = Boolean(sid && onFocusSection);
                      return (
                        <li key={`${issue.code}-${sid || "doc"}-${idx}`}>
                          {clickable ? (
                            <button
                              type="button"
                              className="text-left underline-offset-2 hover:underline"
                              onClick={() => onFocusSection?.(String(sid))}
                            >
                              <span className="font-medium">[{issue.severity}]</span>{" "}
                              {sid ? `${sid}: ` : ""}
                              {issue.message}
                            </button>
                          ) : (
                            <>
                              <span className="font-medium">[{issue.severity}]</span>{" "}
                              {sid ? `${sid}: ` : ""}
                              {issue.message}
                            </>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </AccordionContent>
              </AccordionItem>
            );
          })}
          {grouped.other.length ? (
            <AccordionItem value="sev-other">
              <AccordionTrigger className="py-2 text-[12px]">Other</AccordionTrigger>
              <AccordionContent className="pb-2">
                <ul className="space-y-1 text-[11px] text-muted-foreground">
                  {grouped.other.map((issue, idx) => (
                    <li key={`other-${idx}`}>
                      [{issue.severity}] {issue.message}
                    </li>
                  ))}
                </ul>
              </AccordionContent>
            </AccordionItem>
          ) : null}
        </Accordion>
      )}

      {errorCount > 0 ? (
        <p className="mt-2 text-[10px] font-medium text-amber-800 dark:text-amber-200">
          Pre-export checklist: resolve {errorCount} error
          {errorCount === 1 ? "" : "s"} before Accept or Markdown export.
        </p>
      ) : null}
    </div>
  );
}
