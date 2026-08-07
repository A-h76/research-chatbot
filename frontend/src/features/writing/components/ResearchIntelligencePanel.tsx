/**
 * Contextual Research Reviewer — one primary task at a time.
 * Modes: assist (idle) | citation | selection | review
 */
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Check, ExternalLink, Loader2, PenLine, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EvidenceInspectorPanel } from "@/features/evidence/components/EvidenceInspectorPanel";
import { ConsensusConflictStrip } from "@/features/evidence/components/ConsensusConflictStrip";
import { ResearchReviewerPanel } from "@/features/writing/components/ResearchReviewerPanel";
import { useEvidenceReason } from "@/features/evidence/hooks/useEvidenceReason";
import { evidenceApi } from "@/features/evidence/api";
import type { EvidenceObjectDTO, ExplainResponse } from "@/features/evidence/types";
import { countCitationMarkers, countWords } from "@/features/projects/projectWorkspaceNav";
import { cn } from "@/lib/utils";

export type ReviewerPanelMode = "assist" | "citation" | "selection" | "review";

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
    (evidence.confidence_band?.charAt(0).toUpperCase() || "") +
    (evidence.confidence_band?.slice(1) || "");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-[14px] font-semibold text-foreground">{citationLabel}</p>
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
            supporting
              ? "bg-emerald-500/12 text-emerald-800 dark:text-emerald-200"
              : "bg-muted text-muted-foreground",
          )}
        >
          {supporting ? <Check className="size-3" aria-hidden /> : null}
          {supporting ? "Supporting" : evidence.relation}
        </span>
      </div>

      <blockquote className="rounded-lg bg-muted/50 px-3.5 py-3 text-[13px] leading-relaxed text-foreground/90">
        &ldquo;{evidence.quote || evidence.claim}&rdquo;
        {evidence.page != null ? (
          <footer className="mt-2 text-[12px] text-muted-foreground">
            — Page {evidence.page}
          </footer>
        ) : null}
      </blockquote>

      <div className="space-y-1">
        <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
          Source
        </p>
        <p className="text-[13px] font-semibold leading-snug text-foreground">
          {evidence.file_title || `Paper #${evidence.file_id}`}
        </p>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="mt-2 h-8 gap-1.5 text-[12px]"
          onClick={() => navigate(`/papers/${evidence.file_id}`)}
        >
          <ExternalLink className="size-3.5" />
          Open Paper
        </Button>
      </div>

      <div className="space-y-1.5">
        <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
          Confidence
        </p>
        <div className="flex items-center gap-2">
          <span className="w-10 shrink-0 text-[12px] font-medium">{bandLabel || "—"}</span>
          <div className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${Math.round(score * 100)}%` }}
            />
          </div>
          <span className="text-[12px] tabular-nums text-muted-foreground">
            {score.toFixed(2)}
          </span>
        </div>
      </div>

      <p className="text-[12px] text-muted-foreground">
        Type · <span className="text-foreground">{evidence.study_type || "—"}</span>
      </p>
    </div>
  );
}

function AssistMode({
  manuscript,
  writingBusy,
  projectId,
  onDraft,
  onCite,
  onReview,
}: {
  manuscript: string;
  writingBusy?: boolean;
  projectId?: number | null;
  onDraft?: (section: "literature_review" | "introduction") => void;
  onCite?: () => void;
  onReview?: () => void;
}) {
  const navigate = useNavigate();
  const words = countWords(manuscript);
  const cites = countCitationMarkers(manuscript);
  const empty = words === 0;
  const established = words >= 400;

  const gapsQ = useQuery({
    queryKey: ["evidence", "gaps", projectId],
    queryFn: () => evidenceApi.gaps(projectId as number),
    enabled: projectId != null,
  });
  const topGaps = (gapsQ.data?.gaps ?? []).slice(0, 3);

  const openRi = (
    <button
      type="button"
      onClick={() => navigate("/research/compare")}
      className="inline-flex items-center gap-1 text-[12px] font-medium text-primary hover:underline"
    >
      Open Research Intelligence
      <ExternalLink className="size-3" />
    </button>
  );

  const gapsBlock =
    topGaps.length > 0 ? (
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
            Research gaps
          </p>
          <button
            type="button"
            onClick={() => navigate("/research/compare?tab=gaps")}
            className="text-[11px] text-muted-foreground hover:text-foreground"
          >
            View all
          </button>
        </div>
        <ul className="space-y-1.5">
          {topGaps.map((g) => (
            <li key={g.id}>
              <button
                type="button"
                onClick={() => navigate("/research/compare?tab=gaps")}
                className="w-full rounded-md px-2 py-1.5 text-left text-[12px] leading-relaxed text-foreground/90 hover:bg-muted/60"
              >
                {g.statement}
              </button>
            </li>
          ))}
        </ul>
      </div>
    ) : projectId != null && !gapsQ.isLoading ? (
      <p className="text-[12px] text-muted-foreground">
        No open gaps yet — extract evidence in Research Intelligence to surface them.
      </p>
    ) : null;

  if (empty) {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <p className="text-[13px] leading-relaxed text-muted-foreground">
            Your draft is empty. Choose how to begin.
          </p>
          <p className="mt-1 text-[12px] text-muted-foreground/80">
            Dhund will draft from accepted evidence in this project.
          </p>
        </div>

        <div className="h-px bg-border/50" aria-hidden />

        <div className="space-y-2">
          {onDraft ? (
            <>
              <Button
                type="button"
                id="write-literature-review"
                className="h-9 w-full gap-1.5 text-[13px]"
                disabled={writingBusy}
                onClick={() => onDraft("literature_review")}
              >
                {writingBusy ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Sparkles className="size-3.5" />
                )}
                Draft literature review
              </Button>
              <Button
                type="button"
                variant="outline"
                className="h-9 w-full gap-1.5 text-[13px]"
                disabled={writingBusy}
                onClick={() => onDraft("introduction")}
              >
                Generate introduction
              </Button>
            </>
          ) : null}
        </div>

        <div className="h-px bg-border/50" aria-hidden />

        {gapsBlock}

        <div className="mt-auto space-y-2">
          {openRi}
          <p className="text-[12px] leading-relaxed text-muted-foreground">
            Or start typing in the manuscript — the assistant adapts as you write.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-5">
      <div>
        <p className="text-[13px] leading-relaxed text-muted-foreground">
          {established
            ? "You're making solid progress. Use suggestions below — or click a citation to inspect evidence."
            : "Keep going. Cite as you write, or ask Dhund for a grounded section when you're ready."}
        </p>
      </div>

      <div className="space-y-2 rounded-lg bg-muted/40 px-3 py-2.5 text-[12px]">
        <div className="flex justify-between gap-2">
          <span className="text-muted-foreground">Progress</span>
          <span className="tabular-nums text-foreground">
            {words} words · {cites} citations
          </span>
        </div>
      </div>

      <div>
        <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
          Suggestions
        </p>
        <ul className="space-y-1">
          {cites === 0 && onCite ? (
            <li>
              <button
                type="button"
                className="w-full rounded-md px-2 py-1.5 text-left text-[13px] text-foreground hover:bg-muted/60"
                onClick={onCite}
              >
                Insert first citation
              </button>
            </li>
          ) : null}
          {!established && onDraft ? (
            <li>
              <button
                type="button"
                id="write-literature-review"
                disabled={writingBusy}
                className="w-full rounded-md px-2 py-1.5 text-left text-[13px] text-foreground hover:bg-muted/60 disabled:opacity-50"
                onClick={() => onDraft("literature_review")}
              >
                {writingBusy ? "Drafting…" : "Draft literature review"}
              </button>
            </li>
          ) : null}
          {onReview ? (
            <li>
              <button
                type="button"
                className="w-full rounded-md px-2 py-1.5 text-left text-[13px] text-foreground hover:bg-muted/60"
                onClick={onReview}
              >
                Review manuscript
              </button>
            </li>
          ) : null}
          <li className="px-2 py-1.5 text-[13px] text-muted-foreground">Continue writing</li>
        </ul>
      </div>

      {gapsBlock}

      <div className="mt-auto space-y-2">
        {openRi}
        {onCite && cites > 0 ? (
          <Button
            type="button"
            variant="outline"
            className="h-9 w-full gap-1.5 text-[13px]"
            onClick={onCite}
          >
            <PenLine className="size-3.5" /> Insert citation
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function SelectionMode({
  stickyText,
  explainStatus,
  explainResult,
  documentId,
  projectId,
  onBound,
}: {
  stickyText: string;
  explainStatus: "idle" | "loading" | "ok" | "error";
  explainResult: ExplainResponse | null;
  documentId?: number | null;
  projectId?: number | null;
  onBound?: () => void;
}) {
  const ri = useEvidenceReason({
    documentId: documentId ?? null,
    projectId: projectId ?? null,
    selectedText: stickyText,
    enabled: documentId != null && projectId != null && stickyText.trim().length > 0,
  });

  return (
    <div className="space-y-4">
      <div>
        <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
          Selection
        </p>
        <p className="mt-2 line-clamp-4 text-[13px] leading-relaxed text-foreground/85">
          {stickyText}
        </p>
      </div>

      {ri.status !== "idle" ? (
        <ConsensusConflictStrip
          status={ri.status}
          consensus={ri.result?.consensus}
          conflict={ri.result?.conflict}
          compact
        />
      ) : null}

      <div id="writing-evidence-rail">
        <EvidenceInspectorPanel
          result={explainResult}
          status={explainStatus}
          stickyText={stickyText}
          documentId={documentId}
          projectId={projectId}
          onBound={onBound}
        />
      </div>
    </div>
  );
}

function modeTitle(mode: ReviewerPanelMode): string {
  switch (mode) {
    case "citation":
      return "Evidence";
    case "selection":
      return "Evidence suggestions";
    case "review":
      return "Review";
    default:
      return "Writing assistant";
  }
}

export function ResearchIntelligencePanel({
  mode = "assist",
  selectedEvidenceId,
  explainResult,
  explainStatus,
  stickyText,
  documentId,
  projectId,
  onBound,
  reviewerRefresh,
  groundedReview,
  manuscript = "",
  writingBusy,
  onDraft,
  onCite,
  onReview,
  onClose,
  className,
}: {
  mode?: ReviewerPanelMode;
  selectedEvidenceId?: number | null;
  explainResult: ExplainResponse | null;
  explainStatus: "idle" | "loading" | "ok" | "error";
  stickyText?: string;
  documentId?: number | null;
  projectId?: number | null;
  onBound?: () => void;
  reviewerRefresh?: number;
  groundedReview?: Parameters<typeof ResearchReviewerPanel>[0]["liveReview"];
  manuscript?: string;
  writingBusy?: boolean;
  onDraft?: (section: "literature_review" | "introduction") => void;
  onCite?: () => void;
  onReview?: () => void;
  onClose?: () => void;
  className?: string;
}) {
  const libraryQuery = useQuery({
    queryKey: ["evidence", "library", projectId],
    queryFn: () => evidenceApi.list(projectId as number),
    enabled: projectId != null && mode === "citation",
  });

  const fromLibrary = useMemo(() => {
    if (selectedEvidenceId == null) return null;
    return (libraryQuery.data?.items ?? []).find((e) => e.id === selectedEvidenceId) ?? null;
  }, [libraryQuery.data, selectedEvidenceId]);

  const fromExplain = useMemo(() => {
    if (selectedEvidenceId == null) return null;
    return explainResult?.evidence?.find((e) => e.id === selectedEvidenceId) ?? null;
  }, [explainResult, selectedEvidenceId]);

  const primary = fromLibrary ?? fromExplain ?? null;
  const navigate = useNavigate();

  return (
    <aside
      className={cn(
        "writing-studio-intelligence flex h-full min-h-0 w-full shrink-0 flex-col border-l border-border/60 bg-background lg:w-[268px]",
        className,
      )}
      aria-label="Research Reviewer"
      data-testid="research-reviewer-panel"
      data-mode={mode}
    >
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-border/40 px-4 pb-2 pt-2.5">
        <h2 className="text-[13px] font-semibold tracking-tight text-foreground">
          {modeTitle(mode)}
        </h2>
        {onClose ? (
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="size-7 text-muted-foreground"
            onClick={onClose}
            aria-label="Close panel"
          >
            <X className="size-3.5" />
          </Button>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4 pt-2 scrollbar-thin">
        {mode === "assist" ? (
          <AssistMode
            manuscript={manuscript}
            writingBusy={writingBusy}
            projectId={projectId}
            onDraft={onDraft}
            onCite={onCite}
            onReview={onReview}
          />
        ) : null}

        {mode === "citation" ? (
          primary ? (
            <SupportingCiteCard
              evidence={primary}
              citationLabel={`Citation [${primary.id}]`}
            />
          ) : (
            <p className="text-[13px] leading-relaxed text-muted-foreground">
              Looking up this citation…
            </p>
          )
        ) : null}

        {mode === "selection" ? (
          <SelectionMode
            stickyText={stickyText || ""}
            explainStatus={explainStatus}
            explainResult={explainResult}
            documentId={documentId}
            projectId={projectId}
            onBound={onBound}
          />
        ) : null}

        {mode === "review" && documentId != null ? (
          <div className="space-y-3">
            <p className="text-[13px] leading-relaxed text-muted-foreground">
              Check unsupported claims and weak evidence before you export.
            </p>
            <ResearchReviewerPanel
              documentId={documentId}
              liveReview={groundedReview}
              refreshKey={reviewerRefresh}
            />
            <button
              type="button"
              onClick={() => navigate("/research/compare?tab=gaps")}
              className="inline-flex items-center gap-1 text-[12px] font-medium text-primary hover:underline"
            >
              Explore research gaps
              <ExternalLink className="size-3" />
            </button>
            <details className="pt-2">
              <summary className="cursor-pointer text-[12px] text-muted-foreground hover:text-foreground">
                Advanced evidence tools
              </summary>
              <div id="writing-evidence-rail" className="mt-2">
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
        ) : null}
      </div>
    </aside>
  );
}
