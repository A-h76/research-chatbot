/**
 * Paper tab: Phase 1.5 Evidence Grading (GRADE / frameworks).
 * This is NOT the Evidence Platform / Research Intelligence EvidenceObject Inspector
 * (that lives in Writing Studio).
 */
import { useMemo } from "react";
import { AlertCircle, Scale } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { AiStateBadge, isPipelineError, usePipeline, usePipelinePhase } from "@/features/pipeline";
import { cn } from "@/lib/utils";
import {
  formatConfidence,
  formatLabel,
  mapEvidence,
  type AssessmentsView,
  type EvidenceRefView,
  type EvidenceViewModel,
  type FrameworkView,
  type OutcomeGradeView,
} from "../mappers/evidence";
import { useWorkspaceFocus } from "../useWorkspaceFocus";

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
      {children}
    </h3>
  );
}

function EvidenceList({ evidence }: { evidence: EvidenceRefView[] }) {
  if (evidence.length === 0) return null;
  return (
    <ul className="mt-2 space-y-1.5" role="list">
      {evidence.map((ev, i) => (
        <li
          key={`${ev.page ?? ""}-${ev.characterRange?.join("-") ?? i}-${ev.textSnippet ?? ""}`}
          className="rounded-md border border-border/80 bg-muted/30 px-2.5 py-1.5 text-xs text-foreground/80"
        >
          {ev.textSnippet && <p className="leading-relaxed">{ev.textSnippet}</p>}
          <p className="mt-1 text-muted-foreground">
            {[
              ev.section ? formatLabel(ev.section) : null,
              ev.page != null ? `p. ${ev.page}` : null,
              formatConfidence(ev.confidence),
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </li>
      ))}
    </ul>
  );
}

function MetaCard({
  title,
  ariaLabel,
  workspaceRef,
  children,
}: {
  title: string;
  ariaLabel: string;
  workspaceRef?: string;
  children: React.ReactNode;
}) {
  return (
    <article
      tabIndex={0}
      data-workspace-ref={workspaceRef}
      aria-label={ariaLabel}
      className={cn(
        "rounded-xl border border-border bg-card p-4 outline-none",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
      )}
    >
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
      <div className="mt-2 space-y-2">{children}</div>
    </article>
  );
}

function FrameworkCard({ fw }: { fw: FrameworkView }) {
  const conf = formatConfidence(fw.confidence);
  return (
    <MetaCard
      title={fw.displayName}
      workspaceRef={fw.key}
      ariaLabel={`${fw.displayName}, grade ${fw.displayGrade ?? "unavailable"}${
        conf ? `, confidence ${conf}` : ""
      }`}
    >
      <p className="text-lg font-medium text-foreground">{fw.displayGrade ?? "—"}</p>
      <p className="text-sm tabular-nums text-muted-foreground" aria-label={conf ? `Confidence ${conf}` : undefined}>
        {conf ?? "—"}
      </p>
      {fw.summary && <p className="text-sm text-foreground/85">{fw.summary}</p>}
      {fw.framework === "grade" && (fw.downgradeFactors.length > 0 || fw.upgradeFactors.length > 0) && (
        <dl className="space-y-1 text-xs text-foreground/80">
          {fw.downgradeFactors.length > 0 && (
            <div>
              <dt className="text-muted-foreground">Downgrade factors</dt>
              <dd>{fw.downgradeFactors.join(", ")}</dd>
            </div>
          )}
          {fw.upgradeFactors.length > 0 && (
            <div>
              <dt className="text-muted-foreground">Upgrade factors</dt>
              <dd>{fw.upgradeFactors.join(", ")}</dd>
            </div>
          )}
        </dl>
      )}
      {fw.framework === "oxford" && (
        <p className="text-xs text-muted-foreground">Oxford CEBM level (not comparable to GRADE).</p>
      )}
      <EvidenceList evidence={fw.evidence} />
    </MetaCard>
  );
}

function OutcomeRow({ item }: { item: OutcomeGradeView }) {
  const conf = formatConfidence(item.confidence);
  return (
    <tr
      data-workspace-ref={item.key}
      tabIndex={0}
      className="border-b border-border last:border-0 outline-none focus-visible:bg-muted/40 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
    >
      <th scope="row" className="px-4 py-2 text-left font-normal text-foreground">
        {item.outcomeName}
      </th>
      <td className="px-4 py-2">{item.displayGrade ?? "—"}</td>
      <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">{conf ?? "—"}</td>
    </tr>
  );
}

function AssessmentsSection({ assessments }: { assessments: AssessmentsView }) {
  const blocks: React.ReactNode[] = [];

  if (assessments.riskOfBias) {
    const rob = assessments.riskOfBias;
    blocks.push(
      <MetaCard
        key="rob"
        title="Risk of bias"
        ariaLabel={`Risk of bias ${rob.overallRisk ?? "unknown"}`}
      >
        <p className="text-base font-medium">{rob.overallRisk ? formatLabel(rob.overallRisk) : "—"}</p>
        <p className="text-sm text-muted-foreground">
          {[
            rob.assessmentTool ? `Tool: ${rob.assessmentTool.toUpperCase()}` : null,
            formatConfidence(rob.confidence),
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
        {rob.domains.length > 0 && (
          <ul className="mt-2 space-y-1.5 text-sm" role="list">
            {rob.domains.map((d) => (
              <li key={d.key} className="rounded-md border border-border/80 px-2.5 py-1.5">
                <span className="font-medium">{d.name}</span>
                {d.riskLevel && (
                  <span className="text-muted-foreground"> — {formatLabel(d.riskLevel)}</span>
                )}
                {d.supportText && <p className="mt-0.5 text-xs text-foreground/80">{d.supportText}</p>}
              </li>
            ))}
          </ul>
        )}
        <EvidenceList evidence={rob.evidence} />
      </MetaCard>,
    );
  }

  if (assessments.consistency) {
    const c = assessments.consistency;
    blocks.push(
      <MetaCard key="consistency" title="Consistency" ariaLabel={`Consistency ${c.level ?? ""}`}>
        <p className="text-base font-medium">{c.level ? formatLabel(c.level) : "—"}</p>
        <p className="text-sm text-muted-foreground">{formatConfidence(c.confidence) ?? "—"}</p>
        {c.findings.length > 0 && (
          <ul className="list-disc pl-5 text-sm" role="list">
            {c.findings.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        )}
        <EvidenceList evidence={c.evidence} />
      </MetaCard>,
    );
  }

  if (assessments.precision) {
    const p = assessments.precision;
    blocks.push(
      <MetaCard key="precision" title="Precision" ariaLabel={`Precision ${p.level ?? ""}`}>
        <p className="text-base font-medium">{p.level ? formatLabel(p.level) : "—"}</p>
        <p className="text-sm text-muted-foreground">{formatConfidence(p.confidence) ?? "—"}</p>
        <dl className="space-y-1 text-xs text-foreground/80">
          {p.effectSizeLabel && (
            <div>
              <dt className="text-muted-foreground">Effect size</dt>
              <dd>{p.effectSizeLabel}</dd>
            </div>
          )}
          {p.confidenceIntervalLabel && (
            <div>
              <dt className="text-muted-foreground">Confidence interval</dt>
              <dd>{p.confidenceIntervalLabel}</dd>
            </div>
          )}
          {p.sampleSize != null && (
            <div>
              <dt className="text-muted-foreground">Sample size</dt>
              <dd>{p.sampleSize}</dd>
            </div>
          )}
        </dl>
        <EvidenceList evidence={p.evidence} />
      </MetaCard>,
    );
  }

  if (assessments.directness) {
    const d = assessments.directness;
    blocks.push(
      <MetaCard key="directness" title="Directness" ariaLabel={`Directness ${d.level ?? ""}`}>
        <p className="text-base font-medium">{d.level ? formatLabel(d.level) : "—"}</p>
        <p className="text-sm text-muted-foreground">{formatConfidence(d.confidence) ?? "—"}</p>
        <EvidenceList evidence={d.evidence} />
      </MetaCard>,
    );
  }

  if (assessments.publicationBias) {
    const pb = assessments.publicationBias;
    blocks.push(
      <MetaCard
        key="pubbias"
        title="Publication bias"
        ariaLabel={`Publication bias ${pb.riskLevel ?? ""}`}
      >
        <p className="text-base font-medium">{pb.riskLevel ? formatLabel(pb.riskLevel) : "—"}</p>
        <p className="text-sm text-muted-foreground">{formatConfidence(pb.confidence) ?? "—"}</p>
        <EvidenceList evidence={pb.evidence} />
      </MetaCard>,
    );
  }

  if (assessments.reportingQuality) {
    const r = assessments.reportingQuality;
    blocks.push(
      <MetaCard key="reporting" title="Reporting quality" ariaLabel="Reporting quality">
        <p className="text-base font-medium">
          {r.score != null ? `${Math.round(r.score)}/100` : "—"}
        </p>
        <p className="text-sm text-muted-foreground">
          {[
            r.guideline ? r.guideline.toUpperCase() : null,
            formatConfidence(r.confidence),
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
        {r.missingItems.length > 0 && (
          <p className="text-xs text-foreground/80">Missing: {r.missingItems.join(", ")}</p>
        )}
        <EvidenceList evidence={r.evidence} />
      </MetaCard>,
    );
  }

  if (blocks.length === 0) return null;

  return (
    <section aria-labelledby="evidence-assessments-heading" className="space-y-3">
      <h2 id="evidence-assessments-heading">
        <SectionHeading>Quality assessments</SectionHeading>
      </h2>
      <div className="grid gap-3 sm:grid-cols-2">{blocks}</div>
    </section>
  );
}

function EvidenceReady({
  view,
  focusRef,
}: {
  view: EvidenceViewModel;
  focusRef?: string | null;
}) {
  useWorkspaceFocus(focusRef);
  if (view.skipped) {
    return (
      <div className="space-y-6">
        <section
          aria-labelledby="evidence-skipped-heading"
          className="rounded-xl border border-border bg-muted/20 px-4 py-5 space-y-2"
        >
          <h2 id="evidence-skipped-heading" className="text-sm font-medium text-foreground">
            Evidence grading skipped
          </h2>
          <p className="text-sm text-foreground/85">
            {view.skipReason ?? "Evidence grading was not required for this document’s routing."}
          </p>
          {view.warnings.length > 0 && (
            <ul className="mt-3 space-y-2" role="list">
              {view.warnings.map((msg) => (
                <li
                  key={msg}
                  className="flex gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm"
                >
                  <AlertCircle className="mt-0.5 size-4 shrink-0 text-sem-warn" aria-hidden />
                  <span>{msg}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    );
  }

  const overallConf = formatConfidence(view.overallGrade?.confidence);
  const summaryConf = formatConfidence(view.summaryConfidence);

  return (
    <div className="space-y-8">
      <section aria-labelledby="evidence-overall-heading" className="space-y-3">
        <h2 id="evidence-overall-heading">
          <SectionHeading>Overall evidence</SectionHeading>
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <MetaCard
            title="Overall grade"
            ariaLabel={`Overall grade ${view.overallGrade?.displayValue ?? "unavailable"}`}
          >
            <p className="text-2xl font-medium text-foreground">
              {view.overallGrade?.displayValue ?? "—"}
            </p>
            {view.overallGrade?.description && (
              <p className="text-sm text-foreground/85">{view.overallGrade.description}</p>
            )}
            {overallConf && (
              <p className="text-xs text-muted-foreground">Grade confidence {overallConf}</p>
            )}
          </MetaCard>
          <MetaCard
            title="Study quality"
            ariaLabel={`Study quality ${view.studyQuality ?? "unavailable"}`}
          >
            <p className="text-2xl font-medium text-foreground">
              {view.studyQuality ? formatLabel(view.studyQuality) : "—"}
            </p>
          </MetaCard>
          <MetaCard
            title="Document confidence"
            ariaLabel={`Document confidence ${summaryConf ?? "unavailable"}`}
          >
            <p className="text-2xl font-medium tabular-nums text-foreground">{summaryConf ?? "—"}</p>
            <p className="text-xs text-muted-foreground">From evidence grading confidence score</p>
          </MetaCard>
        </div>
      </section>

      {view.frameworks.length > 0 && (
        <section aria-labelledby="evidence-frameworks-heading" className="space-y-3">
          <h2 id="evidence-frameworks-heading">
            <SectionHeading>Frameworks</SectionHeading>
          </h2>
          <p className="text-xs text-muted-foreground">
            Frameworks use different scales — grades are shown separately and are not compared.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {view.frameworks.map((fw) => (
              <FrameworkCard key={fw.key} fw={fw} />
            ))}
          </div>
        </section>
      )}

      {view.outcomeGrades.length > 0 && (
        <section aria-labelledby="evidence-outcomes-heading" className="space-y-2">
          <h2 id="evidence-outcomes-heading">
            <SectionHeading>Outcome grades</SectionHeading>
          </h2>
          <p className="text-xs text-muted-foreground">
            Outcome rows reflect the document aggregate applied per outcome — not independent
            re-grading.
          </p>
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-sm">
              <caption className="sr-only">Outcome grades derived from the document aggregate</caption>
              <thead>
                <tr className="border-b border-border bg-muted/40 text-left text-xs text-muted-foreground">
                  <th scope="col" className="px-4 py-2 font-medium">
                    Outcome
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium">
                    Grade
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium text-right">
                    Confidence
                  </th>
                </tr>
              </thead>
              <tbody>
                {view.outcomeGrades.map((o) => (
                  <OutcomeRow key={o.key} item={o} />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <AssessmentsSection assessments={view.assessments} />

      {view.warnings.length > 0 && (
        <section aria-labelledby="evidence-warnings-heading" className="space-y-2">
          <h2 id="evidence-warnings-heading">
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

      {view.errors.length > 0 && (
        <section aria-labelledby="evidence-errors-heading" className="space-y-2">
          <h2 id="evidence-errors-heading">
            <SectionHeading>Grading issues</SectionHeading>
          </h2>
          <ul className="space-y-2" role="list">
            {view.errors.map((msg) => (
              <li
                key={msg}
                className="flex gap-2 rounded-lg border border-sem-error/30 bg-sem-error/5 px-3 py-2 text-sm text-sem-error"
              >
                <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
                <span>{msg}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function EvidenceLoading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading evidence grading">
      <div className="grid gap-3 sm:grid-cols-3">
        <Skeleton className="h-28 rounded-xl" />
        <Skeleton className="h-28 rounded-xl" />
        <Skeleton className="h-28 rounded-xl" />
      </div>
      <Skeleton className="h-32 w-full rounded-xl" />
    </div>
  );
}

/**
 * Evidence tab — EvidenceGrades from evidence_grading (M8).
 * Bound to GET …/phases/evidence_grading via M1 hooks.
 */
export function PaperEvidenceTab({
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

  const hasPhase =
    pipeline != null &&
    (pipeline.phases.includes("evidence_grading") ||
      "evidence_grading" in (pipeline.phase_results ?? {}));

  const phaseQuery = usePipelinePhase(fileId, "evidence_grading", {
    enabled: hasPhase,
  });

  const view = useMemo(() => {
    const raw = phaseQuery.data?.result ?? pipeline?.phase_results?.evidence_grading ?? null;
    return mapEvidence(raw);
  }, [phaseQuery.data, pipeline]);

  const waitingOnPipeline =
    derived.isQueued ||
    derived.isRunning ||
    metaStatus === "pending" ||
    metaStatus === "running";

  const loading =
    pipelineLoading ||
    (hasPhase && phaseQuery.isLoading && !view) ||
    (waitingOnPipeline && !view && !derived.isError);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <AiStateBadge derived={derived} metaStatus={metaStatus} />
        </div>
        <EvidenceLoading />
      </div>
    );
  }

  if (pipelineError || (hasPhase && phaseQuery.isError && !view)) {
    const err = phaseQuery.error ?? pipelineErr;
    const message = isPipelineError(err)
      ? err.code === "not_found"
        ? "Evidence grading is not available for this paper yet."
        : err.details || err.code
      : "Could not load evidence grading.";
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
          icon={<Scale className="size-8" />}
          title="No evidence grading yet"
          description={
            waitingOnPipeline
              ? "Evidence grading is still running. This tab will fill in when the phase completes."
              : "No evidence_grading result is available for this paper. Run Phase 1 analysis to grade evidence quality."
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
          <Scale className="size-3.5" aria-hidden />
          Evidence
        </span>
      </div>
      <EvidenceReady view={view} focusRef={focusRef} />
    </div>
  );
}
