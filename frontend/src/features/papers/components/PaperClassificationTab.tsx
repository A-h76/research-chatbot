import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  Beaker,
  BookOpen,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  Dna,
  Network,
  Tags,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { AiStateBadge, isPipelineError, usePipeline, usePipelinePhase } from "@/features/pipeline";
import { cn } from "@/lib/utils";
import {
  buildProfileSummary,
  buildResearchContextLine,
  confidenceBand,
  formatClassificationLabel,
  formatConfidence,
  formatConfidenceBand,
  humanizeEvidenceLine,
  isConfidentDecision,
  mapClassification,
  orderedProfileDecisions,
  profileDecisionLabel,
  profileDecisionSummary,
  profilePossibleLabel,
  type AnalysisSummaryView,
  type ClassificationDecisionView,
  type ClassificationViewModel,
  type DecisionFamilyKey,
} from "../mappers/classification";
import { useWorkspaceFocus } from "../useWorkspaceFocus";

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
      {children}
    </h3>
  );
}

const FAMILY_ICON: Record<DecisionFamilyKey, typeof Dna> = {
  domain: Dna,
  document_type: BookOpen,
  study_design: Beaker,
  reporting_guideline: ClipboardList,
};

const PRIMARY_TOPIC_LIMIT = 12;

function ProfileSummaryCard({ text }: { text: string }) {
  return (
    <section
      aria-labelledby="profile-summary-heading"
      className="rounded-xl border border-border bg-card px-4 py-4 sm:px-5"
    >
      <h2 id="profile-summary-heading">
        <SectionHeading>Summary</SectionHeading>
      </h2>
      <p className="mt-2 text-[14px] leading-relaxed text-foreground/90">{text}</p>
    </section>
  );
}

function ProfileIdentityRow({ decision }: { decision: ClassificationDecisionView }) {
  const [whyOpen, setWhyOpen] = useState(false);
  const titleId = `profile-decision-${decision.family}-title`;
  const labelId = `profile-decision-${decision.family}-label`;
  const confident = isConfidentDecision(decision);
  const band = confidenceBand(confident ? decision.confidence : undefined);
  const label = profileDecisionLabel(decision);
  const possible = profilePossibleLabel(decision);
  const evidence = decision.evidence.map(humanizeEvidenceLine).filter(Boolean);
  const Icon = FAMILY_ICON[decision.family];

  return (
    <article
      data-workspace-ref={decision.family}
      aria-labelledby={`${titleId} ${labelId}`}
      className="px-4 py-3.5 sm:px-5"
    >
      <div className="flex items-start gap-2.5">
        <Icon className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" aria-hidden />
        <div className="min-w-0 flex-1">
          <header className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-0.5">
            <h3
              id={titleId}
              className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground"
            >
              {decision.familyTitle}
            </h3>
            <p className="text-[10px] text-muted-foreground">{formatConfidenceBand(band)}</p>
          </header>
          <p
            id={labelId}
            className={cn(
              "mt-0.5 text-[14px] font-semibold tracking-tight",
              confident ? "text-foreground" : "text-muted-foreground",
            )}
          >
            {label}
          </p>
          <p className="mt-1 text-[12px] leading-snug text-muted-foreground">
            {profileDecisionSummary(decision)}
          </p>

          {(evidence.length > 0 || possible || decision.reasoning) && (
            <div className="mt-2">
              <button
                type="button"
                className="inline-flex items-center gap-1 text-[11px] font-medium text-foreground/80 hover:text-foreground"
                aria-expanded={whyOpen}
                onClick={() => setWhyOpen((v) => !v)}
              >
                {whyOpen ? (
                  <ChevronDown className="size-3" aria-hidden />
                ) : (
                  <ChevronRight className="size-3" aria-hidden />
                )}
                Why?
              </button>
              {whyOpen && (
                <div className="mt-1.5 space-y-1.5 rounded-lg border border-border/80 bg-muted/25 px-2.5 py-2">
                  {possible && (
                    <p className="text-[11px] text-muted-foreground">
                      Weak signal suggested{" "}
                      <span className="font-medium text-foreground/85">{possible}</span>
                      {decision.confidence != null && (
                        <> ({formatConfidence(decision.confidence)})</>
                      )}
                      . Shown as not identified until confidence improves.
                    </p>
                  )}
                  {evidence.length > 0 ? (
                    <ul className="space-y-1" role="list">
                      {evidence.map((line) => (
                        <li
                          key={line}
                          className="flex gap-2 text-[11px] leading-relaxed text-foreground/85"
                        >
                          <span className="text-muted-foreground" aria-hidden>
                            ·
                          </span>
                          <span>{line}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-[11px] text-muted-foreground">
                      No supporting concepts were attached to this decision.
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

function PrimaryTopics({ keywords }: { keywords: string[] }) {
  const shown = keywords.slice(0, PRIMARY_TOPIC_LIMIT);
  const overflow = keywords.length - shown.length;

  return (
    <section aria-labelledby="profile-topics-heading" className="space-y-2">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id="profile-topics-heading">
          <SectionHeading>Primary topics</SectionHeading>
        </h2>
        <p className="text-[11px] tabular-nums text-muted-foreground">
          {keywords.length}
        </p>
      </div>
      <ul className="flex flex-wrap gap-1.5" role="list">
        {shown.map((kw) => (
          <li
            key={kw}
            className="rounded-md border border-border/90 bg-muted/30 px-2 py-0.5 text-[12px] text-foreground"
          >
            {kw}
          </li>
        ))}
        {overflow > 0 && (
          <li className="px-1.5 py-0.5 text-[12px] text-muted-foreground">+{overflow} more</li>
        )}
      </ul>
    </section>
  );
}

function AnalysisSummaryStrip({ summary }: { summary: AnalysisSummaryView }) {
  const contextLine = buildResearchContextLine(summary);
  const rows: [string, string | undefined][] = [
    ["Audience", summary.audience ? formatClassificationLabel(summary.audience) : undefined],
    ["Readiness", summary.readiness ? formatClassificationLabel(summary.readiness) : undefined],
    ["Routing", summary.routing ? formatClassificationLabel(summary.routing) : undefined],
    [
      "Reliability",
      summary.reliability ? formatClassificationLabel(summary.reliability) : undefined,
    ],
  ];

  const visible = rows.filter(([, v]) => Boolean(v));
  if (visible.length === 0 && !contextLine) return null;

  return (
    <section aria-labelledby="profile-context-heading" className="space-y-2">
      <h2 id="profile-context-heading">
        <SectionHeading>Research context</SectionHeading>
      </h2>
      {contextLine && (
        <p className="text-[13px] leading-relaxed text-muted-foreground">{contextLine}</p>
      )}
      {visible.length > 0 && (
        <dl className="rounded-xl border border-border bg-card px-4 py-2 divide-y divide-border">
          {visible.map(([label, value]) => (
            <div
              key={label}
              className="grid grid-cols-[8rem_1fr] gap-2 py-1.5 text-sm sm:grid-cols-[10rem_1fr]"
            >
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="min-w-0 break-words text-foreground">{value}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

function ExploreRelated({ fileId }: { fileId: number }) {
  const links = [
    { tab: "structure", label: "Structure", hint: "Sections & outline" },
    { tab: "entities", label: "Entities", hint: "Concepts & named terms" },
    { tab: "evidence", label: "Evidence", hint: "Claims & grades" },
  ] as const;

  return (
    <section aria-labelledby="profile-explore-heading" className="space-y-2">
      <h2 id="profile-explore-heading">
        <SectionHeading>Explore</SectionHeading>
      </h2>
      <ul className="grid gap-2 sm:grid-cols-3" role="list">
        {links.map(({ tab, label, hint }) => (
          <li key={tab}>
            <Link
              to={`/papers/${fileId}?tab=${tab}`}
              className={cn(
                "flex h-full flex-col gap-0.5 rounded-xl border border-border bg-card px-3 py-2.5",
                "text-left transition-colors hover:bg-muted/40",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              )}
            >
              <span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-foreground">
                <Network className="size-3.5 text-muted-foreground" aria-hidden />
                {label}
              </span>
              <span className="text-[11px] text-muted-foreground">{hint}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ProfileDetails({ view }: { view: ClassificationViewModel }) {
  const [open, setOpen] = useState(false);
  const hasDetails =
    view.candidates.length > 0 ||
    view.pipelineVersion ||
    view.processingTimeMs != null ||
    view.decisions.some((d) => d.confidence != null);

  if (!hasDetails) return null;

  return (
    <section aria-labelledby="profile-details-heading" className="space-y-2">
      <button
        type="button"
        id="profile-details-heading"
        className="flex w-full items-center gap-2 text-left"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? (
          <ChevronDown className="size-3.5 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-3.5 text-muted-foreground" />
        )}
        <SectionHeading>Details</SectionHeading>
        <span className="text-[11px] text-muted-foreground">Scores & candidates</span>
      </button>
      {open && (
        <div className="space-y-4 rounded-xl border border-border bg-card p-4">
          <dl className="grid gap-2 text-[12px] sm:grid-cols-2">
            {orderedProfileDecisions(view.decisions).map((d) => (
              <div key={d.family} className="flex justify-between gap-2 border-b border-border/60 pb-1.5">
                <dt className="text-muted-foreground">{d.familyTitle}</dt>
                <dd className="tabular-nums text-foreground/85">
                  {formatConfidence(d.confidence) ?? "—"}
                </dd>
              </div>
            ))}
          </dl>
          {view.candidates.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <caption className="sr-only">Candidate labels sorted by score</caption>
                <thead>
                  <tr className="border-b border-border text-left text-xs text-muted-foreground">
                    <th scope="col" className="py-1.5 font-medium">
                      Label
                    </th>
                    <th scope="col" className="py-1.5 text-right font-medium">
                      Score
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {view.candidates.map((c) => (
                    <tr key={c.key} className="border-b border-border/70 last:border-0">
                      <td className="py-1.5">
                        <span className="text-foreground">{c.displayLabel}</span>
                        <span className="ml-2 text-xs text-muted-foreground">
                          {formatClassificationLabel(c.family)}
                        </span>
                      </td>
                      <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                        {formatConfidence(c.confidence)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {(view.pipelineVersion || view.processingTimeMs != null) && (
            <p className="text-[11px] text-muted-foreground">
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
      )}
    </section>
  );
}

function ResearchProfileReady({
  view,
  fileId,
  focusRef,
}: {
  view: ClassificationViewModel;
  fileId: number;
  focusRef?: string | null;
}) {
  useWorkspaceFocus(focusRef);
  const identity = orderedProfileDecisions(view.decisions);
  const summary = buildProfileSummary(view);

  return (
    <div className="space-y-6">
      {summary && <ProfileSummaryCard text={summary} />}

      <section aria-labelledby="profile-identity-heading" className="space-y-2">
        <h2 id="profile-identity-heading">
          <SectionHeading>Identity</SectionHeading>
        </h2>
        <div className="overflow-hidden rounded-xl border border-border bg-card sm:grid sm:grid-cols-2 sm:divide-x sm:divide-border">
          {identity.map((d, i) => (
            <div
              key={d.family}
              className={cn(
                "border-b border-border",
                i === identity.length - 1 && "max-sm:border-b-0",
                i >= 2 && "sm:border-b-0",
              )}
            >
              <ProfileIdentityRow decision={d} />
            </div>
          ))}
        </div>
      </section>

      {view.keywords.length > 0 && <PrimaryTopics keywords={view.keywords} />}

      {view.analysisSummary && <AnalysisSummaryStrip summary={view.analysisSummary} />}

      <ExploreRelated fileId={fileId} />

      <ProfileDetails view={view} />

      {view.warnings.length > 0 && (
        <section aria-labelledby="profile-notes-heading" className="space-y-2">
          <h2 id="profile-notes-heading">
            <SectionHeading>Notes</SectionHeading>
          </h2>
          <ul className="space-y-2" role="list">
            {view.warnings.map((msg) => (
              <li
                key={msg}
                className="flex gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm text-foreground/85"
              >
                <AlertCircle className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                <span>{msg}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function ResearchProfileLoading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading research profile">
      <Skeleton className="h-4 w-40" />
      <Skeleton className="h-48 w-full rounded-xl" />
    </div>
  );
}

/**
 * Research Profile tab (URL id still `classification`) — Pass 2 + analysis_context.
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
        <ResearchProfileLoading />
      </div>
    );
  }

  if (pipelineError || (hasClassificationPhase && classificationQuery.isError && !view)) {
    const err = classificationQuery.error ?? pipelineErr;
    const message = isPipelineError(err)
      ? err.code === "not_found"
        ? "Research profile is not available for this paper yet."
        : err.details || err.code
      : "Could not load research profile.";
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
          title="No research profile yet"
          description={
            waitingOnPipeline
              ? "Profiling is still running. This tab will fill in when the phase completes."
              : "No profile is available for this paper yet. Run Phase 1 analysis to understand document type and domain."
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
          Research profile
        </span>
      </div>
      <ResearchProfileReady view={view} fileId={fileId} focusRef={focusRef} />
    </div>
  );
}
