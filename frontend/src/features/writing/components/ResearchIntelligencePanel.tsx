/**
 * Research Intelligence — Dhund differentiator around the familiar manuscript.
 * Phase B: Supporting cite card + Consensus/Conflict + Confidence + Reviewer.
 * Reserved slots for Related Papers / Graph / Gaps (later).
 */
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Check, ExternalLink, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EvidenceInspectorPanel } from "@/features/evidence/components/EvidenceInspectorPanel";
import { ConsensusConflictStrip } from "@/features/evidence/components/ConsensusConflictStrip";
import { ResearchReviewerPanel } from "@/features/writing/components/ResearchReviewerPanel";
import { ResearchConfidenceStrip } from "@/features/writing/components/ResearchConfidenceStrip";
import { useEvidenceReason } from "@/features/evidence/hooks/useEvidenceReason";
import { evidenceApi } from "@/features/evidence/api";
import type { EvidenceObjectDTO, ExplainResponse } from "@/features/evidence/types";
import { cn } from "@/lib/utils";

function confidenceScore(band: string | undefined): number {
  const b = (band || "").toLowerCase();
  if (b === "high") return 0.86;
  if (b === "moderate") return 0.62;
  if (b === "low") return 0.34;
  return 0.5;
}

function SupportingCiteCard({
  evidence,
  citationLabel,
}: {
  evidence: EvidenceObjectDTO;
  citationLabel: string;
}) {
  const navigate = useNavigate();
  const supporting =
    evidence.relation === "supports" || evidence.status === "accepted";
  const score = confidenceScore(evidence.confidence_band);
  const bandLabel =
    evidence.confidence_band?.charAt(0).toUpperCase() +
    (evidence.confidence_band?.slice(1) || "");

  return (
    <section className="space-y-3" aria-label="Supporting evidence">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-semibold text-foreground">{citationLabel}</p>
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
            supporting
              ? "bg-emerald-500/15 text-emerald-800 dark:text-emerald-200"
              : "bg-muted text-muted-foreground",
          )}
        >
          {supporting ? <Check className="size-3" aria-hidden /> : null}
          {supporting ? "Supporting" : evidence.relation}
        </span>
      </div>

      <blockquote className="rounded-md bg-muted/50 px-3 py-2.5 text-[13px] leading-relaxed text-foreground/90">
        &ldquo;{evidence.quote || evidence.claim}&rdquo;
        {evidence.page != null ? (
          <footer className="mt-2 text-[12px] text-muted-foreground">
            — Page {evidence.page}
          </footer>
        ) : null}
      </blockquote>

      <div className="space-y-1">
        <p className="text-[13px] font-medium leading-snug text-foreground">
          {evidence.file_title || `Paper #${evidence.file_id}`}
        </p>
        {evidence.study_type ? (
          <p className="text-[12px] text-muted-foreground">{evidence.study_type}</p>
        ) : null}
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="mt-1.5 h-8 gap-1.5 text-[12px]"
          onClick={() => navigate(`/papers/${evidence.file_id}`)}
        >
          <ExternalLink className="size-3.5" />
          Open Paper
        </Button>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[12px]">
          <span className="text-muted-foreground">Confidence</span>
          <span className="font-medium tabular-nums text-foreground">
            {bandLabel || "—"} · {score.toFixed(2)}
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-[width]"
            style={{ width: `${Math.round(score * 100)}%` }}
          />
        </div>
      </div>

      {evidence.study_type ? (
        <p className="text-[12px] text-muted-foreground">
          Type · <span className="text-foreground">{evidence.study_type}</span>
        </p>
      ) : null}
    </section>
  );
}

const RESERVED = [
  { id: "related", label: "Related Papers" },
  { id: "graph", label: "Knowledge Graph" },
  { id: "gaps", label: "Research Gap" },
  { id: "suggest", label: "Suggested Improvements" },
] as const;

export function ResearchIntelligencePanel({
  selectedEvidenceId,
  explainResult,
  explainStatus,
  stickyText,
  documentId,
  projectId,
  onBound,
  reviewerRefresh,
  groundedMetrics,
  groundedReview,
  onClose,
  className,
}: {
  selectedEvidenceId?: number | null;
  explainResult: ExplainResponse | null;
  explainStatus: "idle" | "loading" | "ok" | "error";
  stickyText?: string;
  documentId?: number | null;
  projectId?: number | null;
  onBound?: () => void;
  reviewerRefresh?: number;
  groundedMetrics?: Parameters<typeof ResearchConfidenceStrip>[0]["metrics"];
  groundedReview?: Parameters<typeof ResearchConfidenceStrip>[0]["review"];
  onClose?: () => void;
  className?: string;
}) {
  const libraryQuery = useQuery({
    queryKey: ["evidence", "library", projectId],
    queryFn: () => evidenceApi.list(projectId as number),
    enabled: projectId != null,
  });

  const fromLibrary = useMemo(() => {
    if (selectedEvidenceId == null) return null;
    return (libraryQuery.data?.items ?? []).find((e) => e.id === selectedEvidenceId) ?? null;
  }, [libraryQuery.data, selectedEvidenceId]);

  const fromExplain = useMemo(() => {
    if (selectedEvidenceId == null) return null;
    return explainResult?.evidence?.find((e) => e.id === selectedEvidenceId) ?? null;
  }, [explainResult, selectedEvidenceId]);

  const primary = fromLibrary ?? fromExplain ?? explainResult?.evidence?.[0] ?? null;

  const ri = useEvidenceReason({
    documentId: documentId ?? null,
    projectId: projectId ?? null,
    selectedText: stickyText || (primary ? `[#${primary.id}]` : ""),
    enabled: documentId != null && projectId != null && Boolean(stickyText || primary),
  });

  return (
    <aside
      className={cn(
        "writing-studio-intelligence flex h-full min-h-0 w-full shrink-0 flex-col border-l border-border bg-background lg:w-[340px]",
        className,
      )}
      aria-label="Research Intelligence"
      data-testid="research-intelligence-panel"
    >
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-border px-3 py-2.5">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
            Cognitive layer
          </p>
          <h2 className="text-sm font-semibold tracking-tight">Research Intelligence</h2>
        </div>
        {onClose ? (
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="size-7"
            onClick={onClose}
            aria-label="Close intelligence panel"
          >
            <X className="size-3.5" />
          </Button>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-3 scrollbar-thin">
        {primary ? (
          <SupportingCiteCard
            evidence={primary}
            citationLabel={`Citation [#${primary.id}]`}
          />
        ) : (
          <p className="rounded-md border border-dashed border-border px-3 py-4 text-[12px] text-muted-foreground">
            Click a citation chip in the manuscript to inspect supporting evidence, confidence, and
            source.
          </p>
        )}

        {(stickyText || primary) && ri.status !== "idle" ? (
          <section className="space-y-1.5">
            <h3 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Consensus &amp; conflict
            </h3>
            <ConsensusConflictStrip
              status={ri.status}
              consensus={ri.result?.consensus}
              conflict={ri.result?.conflict}
              compact
            />
          </section>
        ) : null}

        {(groundedMetrics || groundedReview) && (
          <section className="space-y-1.5">
            <h3 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Draft confidence
            </h3>
            <ResearchConfidenceStrip
              metrics={groundedMetrics}
              review={groundedReview}
              reviewerVersion={groundedReview?.reviewer_version}
            />
          </section>
        )}

        {documentId != null ? (
          <section className="space-y-1.5">
            <h3 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Reviewer
            </h3>
            <ResearchReviewerPanel
              documentId={documentId}
              liveReview={groundedReview}
              refreshKey={reviewerRefresh}
            />
          </section>
        ) : null}

        <section className="space-y-1.5 border-t border-border pt-3">
          <h3 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Coming in Dhund
          </h3>
          <ul className="space-y-1">
            {RESERVED.map((r) => (
              <li
                key={r.id}
                className="rounded-md border border-dashed border-border/80 px-2.5 py-1.5 text-[12px] text-muted-foreground"
              >
                {r.label}
              </li>
            ))}
          </ul>
        </section>

        <details className="rounded-md border border-border">
          <summary className="cursor-pointer px-2.5 py-2 text-[12px] font-medium text-muted-foreground">
            Full evidence inspector
          </summary>
          <div id="writing-evidence-rail" className="border-t border-border p-1">
            <EvidenceInspectorPanel
              result={explainResult}
              status={explainStatus}
              stickyText={stickyText}
              documentId={documentId}
              projectId={projectId}
              onBound={onBound}
            />
          </div>
        </details>
      </div>
    </aside>
  );
}
