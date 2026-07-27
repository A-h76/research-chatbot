import { AlertCircle, Tags } from "lucide-react";
import { useMemo } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { AiStateBadge, isPipelineError, usePipeline, usePipelinePhase } from "@/features/pipeline";
import { cn } from "@/lib/utils";
import {
  formatClassificationLabel,
  formatConfidence,
  mapClassification,
  type AnalysisSummaryView,
  type ClassificationDecisionView,
  type ClassificationViewModel,
} from "../mappers/classification";
import { useWorkspaceFocus } from "../useWorkspaceFocus";

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
      {children}
    </h3>
  );
}

function DecisionCard({ decision }: { decision: ClassificationDecisionView }) {
  const titleId = `classify-decision-${decision.family}-title`;
  const labelId = `classify-decision-${decision.family}-label`;
  const confidenceText = formatConfidence(decision.confidence);
  const ariaLabel = [
    decision.familyTitle,
    decision.displayLabel ?? "no label",
    confidenceText ? `confidence ${confidenceText}` : null,
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <article
      tabIndex={0}
      data-workspace-ref={decision.family}
      aria-labelledby={`${titleId} ${labelId}`}
      aria-label={ariaLabel}
      className={cn(
        "rounded-xl border border-border bg-card p-4 outline-none",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
      )}
    >
      <header className="flex items-start justify-between gap-3">
        <h3 id={titleId} className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {decision.familyTitle}
        </h3>
        <p
          className="shrink-0 text-sm tabular-nums text-muted-foreground"
          aria-label={confidenceText ? `Confidence ${confidenceText}` : "Confidence unavailable"}
        >
          {confidenceText ?? "—"}
        </p>
      </header>
      <p id={labelId} className="mt-2 text-base font-medium text-foreground">
        {decision.displayLabel ?? "—"}
      </p>
      {decision.reasoning && (
        <p className="mt-3 text-sm text-foreground/85">{decision.reasoning}</p>
      )}
      {decision.evidence.length > 0 && (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-foreground/80" role="list">
          {decision.evidence.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
    </article>
  );
}

function AnalysisSummaryStrip({ summary }: { summary: AnalysisSummaryView }) {
  const rows: [string, string | undefined][] = [
    ["Audience", summary.audience ? formatClassificationLabel(summary.audience) : undefined],
    ["Readiness", summary.readiness ? formatClassificationLabel(summary.readiness) : undefined],
    ["Routing", summary.routing ? formatClassificationLabel(summary.routing) : undefined],
    [
      "Reliability",
      summary.reliability ? formatClassificationLabel(summary.reliability) : undefined,
    ],
    ["Overall confidence", formatConfidence(summary.overallConfidence)],
  ];

  const visible = rows.filter(([, v]) => Boolean(v));
  if (visible.length === 0) return null;

  return (
    <section aria-labelledby="classify-context-heading" className="space-y-2">
      <h2 id="classify-context-heading">
        <SectionHeading>Analysis context</SectionHeading>
      </h2>
      <dl className="rounded-xl border border-border bg-card px-4 py-2 divide-y divide-border">
        {visible.map(([label, value]) => (
          <div
            key={label}
            className="grid grid-cols-[8rem_1fr] gap-2 py-1.5 text-sm sm:grid-cols-[10rem_1fr]"
          >
            <dt className="text-muted-foreground">{label}</dt>
            <dd className="min-w-0 text-foreground break-words">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function ClassificationReady({
  view,
  focusRef,
}: {
  view: ClassificationViewModel;
  focusRef?: string | null;
}) {
  useWorkspaceFocus(focusRef);
  return (
    <div className="space-y-8">
      <section aria-labelledby="classify-decisions-heading" className="space-y-3">
        <h2 id="classify-decisions-heading">
          <SectionHeading>Decisions</SectionHeading>
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {view.decisions.map((d) => (
            <DecisionCard key={d.family} decision={d} />
          ))}
        </div>
      </section>

      {view.analysisSummary && <AnalysisSummaryStrip summary={view.analysisSummary} />}

      {view.candidates.length > 0 && (
        <section aria-labelledby="classify-candidates-heading" className="space-y-2">
          <h2 id="classify-candidates-heading">
            <SectionHeading>Candidate labels</SectionHeading>
          </h2>
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-sm">
              <caption className="sr-only">
                Candidate classification labels sorted by confidence, highest first
              </caption>
              <thead>
                <tr className="border-b border-border bg-muted/40 text-left text-xs text-muted-foreground">
                  <th scope="col" className="px-4 py-2 font-medium">
                    Label
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium text-right">
                    Score
                  </th>
                </tr>
              </thead>
              <tbody>
                {view.candidates.map((c) => (
                  <tr key={c.key} className="border-b border-border last:border-0">
                    <td className="px-4 py-2">
                      <span className="text-foreground">{c.displayLabel}</span>
                      <span className="ml-2 text-xs text-muted-foreground">
                        {formatClassificationLabel(c.family)}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">
                      {formatConfidence(c.confidence)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {view.keywords.length > 0 && (
        <section aria-labelledby="classify-keywords-heading" className="space-y-2">
          <h2 id="classify-keywords-heading">
            <SectionHeading>Detected keywords</SectionHeading>
          </h2>
          <ul className="flex flex-wrap gap-1.5" role="list">
            {view.keywords.map((kw) => (
              <li
                key={kw}
                className="rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs text-foreground"
              >
                {kw}
              </li>
            ))}
          </ul>
        </section>
      )}

      {view.warnings.length > 0 && (
        <section aria-labelledby="classify-warnings-heading" className="space-y-2">
          <h2 id="classify-warnings-heading">
            <SectionHeading>Warnings</SectionHeading>
          </h2>
          <ul className="space-y-2" role="list">
            {view.warnings.map((msg) => (
              <li
                key={msg}
                className="flex gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm"
              >
                <AlertCircle className="mt-0.5 size-4 shrink-0 text-sem-warn" aria-hidden />
                <span>{msg}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {(view.pipelineVersion || view.processingTimeMs != null) && (
        <p className="text-xs text-muted-foreground">
          {view.pipelineVersion && <>Pipeline {view.pipelineVersion}</>}
          {view.pipelineVersion && view.processingTimeMs != null && " · "}
          {view.processingTimeMs != null && (
            <>
              {view.processingTimeMs < 10
                ? view.processingTimeMs.toFixed(2)
                : Math.round(view.processingTimeMs)}{" "}
              ms
            </>
          )}
        </p>
      )}
    </div>
  );
}

function ClassificationLoading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading classification">
      <Skeleton className="h-4 w-40" />
      <div className="grid gap-3 sm:grid-cols-2">
        <Skeleton className="h-28 w-full rounded-xl" />
        <Skeleton className="h-28 w-full rounded-xl" />
        <Skeleton className="h-28 w-full rounded-xl" />
        <Skeleton className="h-28 w-full rounded-xl" />
      </div>
    </div>
  );
}

/**
 * Classification tab — Pass 2 ClassificationResult + analysis_context summary (M6).
 * Bound to GET …/phases/classification and GET …/phases/analysis_context via M1 hooks.
 */
export function PaperClassificationTab({
  fileId,
  metaStatus,
  focusRef,
}: {
  fileId: number;
  metaStatus?: string | null;
  focusRef?: string | null;
}) {
  const { pipeline, derived, isLoading: pipelineLoading, isError: pipelineError, error: pipelineErr } =
    usePipeline(fileId);

  const hasClassificationPhase =
    pipeline != null &&
    (pipeline.phases.includes("classification") ||
      "classification" in (pipeline.phase_results ?? {}));

  const hasContextPhase =
    pipeline != null &&
    (pipeline.phases.includes("analysis_context") ||
      "analysis_context" in (pipeline.phase_results ?? {}));

  const classificationQuery = usePipelinePhase(fileId, "classification", {
    enabled: hasClassificationPhase,
  });

  const contextQuery = usePipelinePhase(fileId, "analysis_context", {
    enabled: hasContextPhase,
  });

  const view = useMemo(() => {
    const clf =
      classificationQuery.data?.result ?? pipeline?.phase_results?.classification ?? null;
    const ctx = contextQuery.data?.result ?? pipeline?.phase_results?.analysis_context ?? null;
    return mapClassification(clf, ctx);
  }, [classificationQuery.data, contextQuery.data, pipeline]);

  const waitingOnPipeline =
    derived.isQueued ||
    derived.isRunning ||
    metaStatus === "pending" ||
    metaStatus === "running";

  const loading =
    pipelineLoading ||
    (hasClassificationPhase && classificationQuery.isLoading && !view) ||
    (waitingOnPipeline && !view && !derived.isError);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <AiStateBadge derived={derived} metaStatus={metaStatus} />
        </div>
        <ClassificationLoading />
      </div>
    );
  }

  if (pipelineError || (hasClassificationPhase && classificationQuery.isError && !view)) {
    const err = classificationQuery.error ?? pipelineErr;
    const message = isPipelineError(err)
      ? err.code === "not_found"
        ? "Classification is not available for this paper yet."
        : err.details || err.code
      : "Could not load classification.";
    return (
      <div className="space-y-4">
        <AiStateBadge derived={derived} metaStatus={metaStatus} />
        <div
          role="alert"
          className={cn(
            "flex gap-2 rounded-xl border border-sem-error/30 bg-sem-error/5 px-4 py-3 text-sm text-sem-error",
          )}
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <span>{message}</span>
        </div>
      </div>
    );
  }

  if (!view || !view.hasContent) {
    return (
      <div className="space-y-4">
        <AiStateBadge derived={derived} metaStatus={metaStatus} />
        <EmptyState
          icon={<Tags className="size-8" />}
          title="No classification yet"
          description={
            waitingOnPipeline
              ? "Classification is still running. This tab will fill in when the phase completes."
              : "No classification result is available for this paper. Run Phase 1 analysis to classify the document."
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <AiStateBadge derived={derived} metaStatus={metaStatus} />
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          <Tags className="size-3.5" aria-hidden />
          Classification
        </span>
      </div>
      <ClassificationReady view={view} focusRef={focusRef} />
    </div>
  );
}
