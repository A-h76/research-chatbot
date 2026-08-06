import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, ChevronDown, ChevronRight, FileText, Layers } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { AiStateBadge, isPipelineError, usePipeline, usePipelinePhase } from "@/features/pipeline";
import { cn } from "@/lib/utils";
import { PaperPhaseEmpty } from "./PaperPhaseEmpty";
import {
  mapStructure,
  type DocumentUnderstandingView,
  type LimitationsNoveltyProfileView,
  type MethodologyField,
  type MethodologyProfileView,
  type QualityAssessmentView,
  type ScientificStructureView,
  type StatisticsProfileView,
} from "../mappers/structure";
import { mapClassification } from "../mappers/classification";
import { structureSectionRefId } from "../mappers/chat";
import { useWorkspaceFocus } from "../useWorkspaceFocus";
import { parseSectionBody } from "./sectionContent";
import { buildDocumentAnalysisReport } from "./documentAnalysis";
import { DocumentAnalysisPanel } from "./DocumentAnalysisPanel";
import { ReferenceBrowser } from "./ReferenceBrowser";

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
      {children}
    </h3>
  );
}

function FramingList({
  label,
  items,
}: {
  label: string;
  items: { text: string; source?: string }[];
}) {
  if (!items.length) return null;
  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <ul className="list-disc space-y-1 pl-4 text-sm text-foreground/90">
        {items.map((item, i) => (
          <li key={`${label}-${i}`}>
            <span>{item.text}</span>
            {item.source ? (
              <span className="ml-1 text-[11px] text-muted-foreground">({item.source})</span>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ScientificFramingPanel({ structure }: { structure: ScientificStructureView }) {
  const present = structure.sectionSkeleton.filter((s) => s.present);
  return (
    <section aria-labelledby="structure-framing-heading" className="space-y-3">
      <h2 id="structure-framing-heading">
        <SectionHeading>Scientific framing</SectionHeading>
      </h2>
      <div className="space-y-4 rounded-xl border border-border bg-card px-4 py-3">
        {present.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {present.map((s) => (
              <span
                key={s.sectionType}
                className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground"
                title={s.heading || s.sectionType}
              >
                {s.sectionType}
              </span>
            ))}
          </div>
        )}
        {structure.problemStatement ? (
          <div className="space-y-1">
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Problem statement
            </p>
            <p className="text-sm leading-relaxed text-foreground/90">
              {structure.problemStatement.text}
            </p>
          </div>
        ) : null}
        <FramingList label="Objectives" items={structure.objectives} />
        <FramingList label="Research questions" items={structure.researchQuestions} />
        <FramingList label="Hypotheses" items={structure.hypotheses} />
        {!structure.objectives.length &&
        !structure.researchQuestions.length &&
        !structure.hypotheses.length &&
        !structure.problemStatement ? (
          <p className="text-[13px] text-muted-foreground">
            No objectives, research questions, or hypotheses were reliably extractable.
          </p>
        ) : null}
      </div>
    </section>
  );
}

function MethodFieldRow({ label, field }: { label: string; field: MethodologyField | null }) {
  if (!field) return null;
  return (
    <div className="space-y-1">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="text-sm leading-relaxed text-foreground/90">
        {field.label && field.kind === "study_design" ? (
          <span className="font-medium">{field.label.replace(/_/g, " ")} · </span>
        ) : null}
        {field.text}
        {field.source ? (
          <span className="ml-1 text-[11px] text-muted-foreground">({field.source})</span>
        ) : null}
      </p>
    </div>
  );
}

function MethodologyPanel({ profile }: { profile: MethodologyProfileView }) {
  const hasMethod =
    Boolean(
      profile.studyDesign ||
        profile.population ||
        profile.sampleSize ||
        profile.intervention ||
        profile.controls ||
        profile.dataset ||
        profile.experimentalSetup ||
        profile.variables.length ||
        profile.codeAvailable ||
        profile.datasetAvailable,
    );
  const hasEvaluation = profile.metrics.length > 0;

  return (
    <div className="space-y-6">
      {hasMethod ? (
        <section aria-labelledby="structure-methodology-heading" className="space-y-3">
          <h2 id="structure-methodology-heading">
            <SectionHeading>Method</SectionHeading>
          </h2>
          <div className="space-y-4 rounded-xl border border-border bg-card px-4 py-3">
            <MethodFieldRow label="Study design" field={profile.studyDesign} />
            <MethodFieldRow label="Population" field={profile.population} />
            <MethodFieldRow label="Sample size" field={profile.sampleSize} />
            <MethodFieldRow label="Intervention" field={profile.intervention} />
            <MethodFieldRow label="Controls" field={profile.controls} />
            <MethodFieldRow label="Training data / Dataset" field={profile.dataset} />
            <MethodFieldRow label="Experimental setup" field={profile.experimentalSetup} />
            <FramingList label="Variables" items={profile.variables} />
            {(profile.codeAvailable || profile.datasetAvailable) && (
              <div className="space-y-1.5 border-t border-border pt-3">
                <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  Author-stated availability
                </p>
                <ul className="list-disc space-y-1 pl-4 text-sm text-foreground/90">
                  {profile.codeAvailable ? (
                    <li>
                      Code · {profile.codeAvailable.text}
                      {profile.codeAvailable.source ? (
                        <span className="ml-1 text-[11px] text-muted-foreground">
                          ({profile.codeAvailable.source})
                        </span>
                      ) : null}
                    </li>
                  ) : null}
                  {profile.datasetAvailable ? (
                    <li>
                      Dataset · {profile.datasetAvailable.text}
                      {profile.datasetAvailable.source ? (
                        <span className="ml-1 text-[11px] text-muted-foreground">
                          ({profile.datasetAvailable.source})
                        </span>
                      ) : null}
                    </li>
                  ) : null}
                </ul>
              </div>
            )}
          </div>
        </section>
      ) : null}

      {hasEvaluation ? (
        <section aria-labelledby="structure-evaluation-heading" className="space-y-3">
          <h2 id="structure-evaluation-heading">
            <SectionHeading>Evaluation</SectionHeading>
          </h2>
          <div className="space-y-4 rounded-xl border border-border bg-card px-4 py-3">
            <FramingList label="Metrics" items={profile.metrics} />
            <p className="text-[11px] text-muted-foreground">
              Reported evaluation measures — not a Dhund quality judgment.
            </p>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function FindingList({
  label,
  items,
  showLabel = false,
}: {
  label: string;
  items: { text: string; label?: string; source?: string }[];
  showLabel?: boolean;
}) {
  if (!items.length) return null;
  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <ul className="list-disc space-y-1 pl-4 text-sm text-foreground/90">
        {items.map((item, i) => (
          <li key={`${label}-${i}`}>
            {showLabel && item.label ? (
              <span className="font-medium">{item.label.replace(/_/g, " ")} · </span>
            ) : null}
            <span>{item.text}</span>
            {item.source ? (
              <span className="ml-1 text-[11px] text-muted-foreground">({item.source})</span>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function StatisticalFindingsPanel({ profile }: { profile: StatisticsProfileView }) {
  return (
    <section aria-labelledby="structure-stats-findings-heading" className="space-y-3">
      <h2 id="structure-stats-findings-heading">
        <SectionHeading>Statistical findings</SectionHeading>
      </h2>
      <div className="space-y-4 rounded-xl border border-border bg-card px-4 py-3">
        <FindingList label="Tests" items={profile.tests} showLabel />
        <FindingList label="P-values" items={profile.pValues} />
        <FindingList label="Confidence intervals" items={profile.confidenceIntervals} />
        <FindingList label="Effect sizes" items={profile.effectSizes} />
        <FindingList label="Other measures" items={profile.otherMeasures} />
        {profile.interpretations.length > 0 ? (
          <div className="space-y-1.5 border-t border-border pt-3">
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Author-stated interpretation
            </p>
            <ul className="list-disc space-y-1 pl-4 text-sm text-foreground/90">
              {profile.interpretations.map((item, i) => (
                <li key={`interp-${i}`}>
                  {item.text}
                  {item.source ? (
                    <span className="ml-1 text-[11px] text-muted-foreground">({item.source})</span>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function LimitationsNoveltyPanel({ profile }: { profile: LimitationsNoveltyProfileView }) {
  return (
    <section aria-labelledby="structure-limitations-novelty-heading" className="space-y-3">
      <h2 id="structure-limitations-novelty-heading">
        <SectionHeading>Limitations &amp; novelty</SectionHeading>
      </h2>
      <div className="space-y-4 rounded-xl border border-border bg-card px-4 py-3">
        <FindingList label="Author-stated limitations" items={profile.limitations} />
        <FindingList label="Author-stated novelty / contributions" items={profile.novelty} />
        <FindingList label="Research gaps" items={profile.researchGaps} />
        <FindingList label="Future work" items={profile.futureWork} />
        <p className="text-[11px] text-muted-foreground">
          Extracted only when authors state these explicitly — no AI quality judgments.
        </p>
      </div>
    </section>
  );
}

function bandLabel(band: string): string {
  switch (band) {
    case "strong":
      return "Strong";
    case "partial":
      return "Partial";
    case "weak":
      return "Weak";
    default:
      return "Not assessed";
  }
}

function statusMark(status: string): string {
  if (status === "pass") return "✓";
  if (status === "missing") return "—";
  return "•";
}

function QualityAssessmentPanel({ assessment }: { assessment: QualityAssessmentView }) {
  return (
    <section aria-labelledby="structure-quality-assessment-heading" className="space-y-3">
      <h2 id="structure-quality-assessment-heading">
        <SectionHeading>Quality assessment</SectionHeading>
      </h2>
      <div className="space-y-4 rounded-xl border border-border bg-card px-4 py-3">
        <p className="text-[12px] text-muted-foreground">
          Inspectable checklist from extracted signals — not an opaque score.
        </p>
        {assessment.sections.map((section) => (
          <div key={section.id} className="space-y-2">
            <p className="text-sm font-medium text-foreground">
              {section.label}:{" "}
              <span className="text-muted-foreground font-normal">{bandLabel(section.band)}</span>
            </p>
            <ul className="space-y-1.5 pl-1 text-sm text-foreground/90">
              {section.items.map((item, i) => (
                <li key={`${section.id}-${i}`} className="flex gap-2">
                  <span className="w-4 shrink-0 tabular-nums text-muted-foreground" aria-hidden>
                    {statusMark(item.status)}
                  </span>
                  <span>
                    {item.text}
                    {item.reason ? (
                      <span className="mt-0.5 block text-[11px] text-muted-foreground">
                        Why: {item.reason}
                      </span>
                    ) : null}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

/** Renders extracted section text with bold in-body headings and full-width prose. */
function SectionContentBody({ content }: { content: string }) {
  const blocks = parseSectionBody(content);
  return (
    <div className="w-full min-w-0 space-y-3 text-sm leading-relaxed text-foreground/90">
      {blocks.map((block, i) => {
        if (block.kind === "heading") {
          return (
            <div key={`h-${i}`} className="w-full min-w-0 space-y-1.5">
              <p className="text-[13px] font-semibold tracking-tight text-foreground">
                {block.label}
              </p>
              {block.rest ? (
                <p className="w-full min-w-0 whitespace-normal break-words text-foreground/85">
                  {block.rest}
                </p>
              ) : null}
            </div>
          );
        }
        return (
          <p
            key={`p-${i}`}
            className="w-full min-w-0 whitespace-normal break-words text-foreground/85"
          >
            {block.text}
          </p>
        );
      })}
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (value == null || value === "") return null;
  return (
    <div className="grid grid-cols-[8rem_1fr] gap-2 py-1.5 text-sm sm:grid-cols-[10rem_1fr]">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-foreground break-words">{value}</dd>
    </div>
  );
}

function StructureReady({
  view,
  focusRef,
  documentTypeLabel,
}: {
  view: DocumentUnderstandingView;
  focusRef?: string | null;
  documentTypeLabel?: string | null;
}) {
  const [openHeading, setOpenHeading] = useState<string | null>(
    view.sections[0]?.heading ?? null,
  );

  useWorkspaceFocus(focusRef);

  useEffect(() => {
    if (!focusRef) return;
    const match = view.sections.find((s) => structureSectionRefId(s) === focusRef);
    if (match) setOpenHeading(match.heading);
  }, [focusRef, view.sections]);

  const journalOrVenue = view.journal || view.venue;
  const analysis = useMemo(
    () => buildDocumentAnalysisReport(view, { documentTypeLabel }),
    [view, documentTypeLabel],
  );

  return (
    <div className="space-y-8">
      <section aria-labelledby="structure-biblio-heading" className="space-y-2">
        <h2 id="structure-biblio-heading" className="sr-only">
          Bibliographic metadata
        </h2>
        <SectionHeading>Document</SectionHeading>
        <dl className="rounded-xl border border-border bg-card px-4 py-2 divide-y divide-border">
          <MetaRow label="Title" value={view.title} />
          <MetaRow label="Subtitle" value={view.subtitle} />
          <MetaRow
            label="Authors"
            value={view.authors.length ? view.authors.join("; ") : undefined}
          />
          <MetaRow label="Journal" value={journalOrVenue} />
          <MetaRow label="Year" value={view.publicationYear} />
          <MetaRow label="Language" value={view.language} />
          <MetaRow
            label="DOI"
            value={
              view.doi ? (
                <a
                  href={`https://doi.org/${view.doi}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  {view.doi}
                </a>
              ) : undefined
            }
          />
        </dl>
        {view.abstract && (
          <div className="rounded-xl border border-border bg-muted/20 p-4">
            <SectionHeading>Abstract</SectionHeading>
            <p className="mt-2 text-sm leading-relaxed text-foreground/85">{view.abstract}</p>
          </div>
        )}
      </section>

      {view.scientificStructure?.hasFraming && (
        <ScientificFramingPanel structure={view.scientificStructure} />
      )}

      {view.methodologyProfile?.hasContent && (
        <MethodologyPanel profile={view.methodologyProfile} />
      )}

      {view.statisticsProfile?.hasContent && (
        <StatisticalFindingsPanel profile={view.statisticsProfile} />
      )}

      {view.limitationsNoveltyProfile?.hasContent && (
        <LimitationsNoveltyPanel profile={view.limitationsNoveltyProfile} />
      )}

      {view.qualityAssessment?.hasContent && (
        <QualityAssessmentPanel assessment={view.qualityAssessment} />
      )}

      {(view.wordCount != null ||
        view.pageCount != null ||
        view.charCount != null ||
        view.sectionCount != null ||
        view.headingCount != null ||
        view.referenceCount != null) && (
        <section aria-labelledby="structure-stats-heading" className="space-y-2">
          <h2 id="structure-stats-heading">
            <SectionHeading>Statistics</SectionHeading>
          </h2>
          <table className="w-full text-sm border border-border rounded-xl overflow-hidden">
            <caption className="sr-only">Document statistics from document understanding</caption>
            <tbody>
              {(
                [
                  ["Word count", view.wordCount],
                  ["Page count", view.pageCount],
                  ["Character count", view.charCount],
                  ["Sections", view.sectionCount],
                  ["Headings", view.headingCount],
                  ["References", view.referenceCount],
                ] as const
              )
                .filter(([, v]) => v != null)
                .map(([label, value]) => (
                  <tr key={label} className="border-b border-border last:border-0">
                    <th scope="row" className="bg-muted/40 px-4 py-2 text-left font-medium text-muted-foreground">
                      {label}
                    </th>
                    <td className="px-4 py-2 tabular-nums">{value}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </section>
      )}

      {view.sections.length > 0 && (
        <section aria-labelledby="structure-sections-heading" className="space-y-2">
          <h2 id="structure-sections-heading">
            <SectionHeading>Sections</SectionHeading>
          </h2>
          <ul className="rounded-xl border border-border divide-y divide-border overflow-hidden">
            {view.sections.map((sec) => {
              const open = openHeading === sec.heading;
              const refId = structureSectionRefId(sec);
              return (
                <li key={sec.heading}>
                  <button
                    type="button"
                    data-workspace-ref={refId}
                    className="flex w-full items-start gap-2 px-4 py-3 text-left text-sm hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
                    aria-expanded={open}
                    onClick={() => setOpenHeading(open ? null : sec.heading)}
                  >
                    {open ? (
                      <ChevronDown className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="font-medium text-foreground">{sec.heading}</span>
                      {sec.sectionType &&
                        sec.sectionType.toLowerCase() !== "other" &&
                        sec.sectionType.toLowerCase() !== "unknown" && (
                          <span className="mt-0.5 flex flex-wrap gap-2 text-xs text-muted-foreground">
                            <span className="rounded-full border border-border px-2 py-0.5">
                              {sec.sectionType}
                            </span>
                          </span>
                        )}
                    </span>
                  </button>
                  {open && sec.content && (
                    <div className="border-t border-border bg-muted/20 px-4 py-4 sm:px-5">
                      <SectionContentBody content={sec.content} />
                    </div>
                  )}
                  {open && !sec.content && (
                    <p className="border-t border-border px-4 py-3 text-xs text-muted-foreground">
                      No section body stored for this heading.
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <ReferenceBrowser references={view.references} />

      <DocumentAnalysisPanel report={analysis} />
    </div>
  );
}

function StructureLoading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading document structure">
      <Skeleton className="h-4 w-40" />
      <Skeleton className="h-24 w-full rounded-xl" />
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-40 w-full rounded-xl" />
    </div>
  );
}

/**
 * Structure tab — Document Understanding (M5).
 * Bound to GET …/pipeline + GET …/phases/document_understanding.
 */
export function PaperStructureTab({
  fileId,
  metaStatus,
  focusRef,
}: {
  fileId: number;
  metaStatus?: string | null;
  focusRef?: string | null;
}) {
  const navigate = useNavigate();
  const { pipeline, derived, isLoading: pipelineLoading, isError: pipelineError, error: pipelineErr } =
    usePipeline(fileId, { metaStatus: metaStatus ?? null });

  const hasDuPhase =
    pipeline != null &&
    (pipeline.phases.includes("document_understanding") ||
      "document_understanding" in (pipeline.phase_results ?? {}));

  const hasClassificationPhase =
    pipeline != null &&
    (pipeline.phases.includes("classification") ||
      "classification" in (pipeline.phase_results ?? {}));

  const phaseQuery = usePipelinePhase(fileId, "document_understanding", {
    enabled: hasDuPhase,
  });

  const classificationQuery = usePipelinePhase(fileId, "classification", {
    enabled: hasClassificationPhase,
  });

  const view = useMemo(
    () => mapStructure(phaseQuery.data?.result),
    [phaseQuery.data],
  );

  const documentTypeLabel = useMemo(() => {
    const clf = mapClassification(
      classificationQuery.data?.result ?? pipeline?.phase_results?.classification ?? null,
    );
    const decision = clf?.decisions.find((d) => d.family === "document_type");
    return decision?.displayLabel ?? decision?.label ?? null;
  }, [classificationQuery.data, pipeline]);

  const waitingOnPipeline =
    derived.isQueued ||
    derived.isRunning ||
    metaStatus === "pending" ||
    metaStatus === "running";

  // Prefer phase payload; fall back to embedded pipeline.phase_results while phase GET loads
  const embedded = useMemo(() => {
    if (view) return null;
    const raw = pipeline?.phase_results?.document_understanding;
    return mapStructure(raw ?? null);
  }, [view, pipeline]);

  const resolved = view ?? embedded;

  const loading =
    pipelineLoading ||
    (hasDuPhase && phaseQuery.isLoading && !resolved) ||
    (waitingOnPipeline && !resolved && !derived.isError);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <AiStateBadge derived={derived} metaStatus={metaStatus} />
        </div>
        <StructureLoading />
      </div>
    );
  }

  if (pipelineError || (hasDuPhase && phaseQuery.isError && !resolved)) {
    const err = phaseQuery.error ?? pipelineErr;
    const message = isPipelineError(err)
      ? err.code === "not_found"
        ? "Document understanding is not available for this paper yet."
        : err.details || err.code
      : "Could not load document structure.";
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

  if (!resolved || !resolved.hasContent) {
    return (
      <div className="space-y-4">
        <AiStateBadge derived={derived} metaStatus={metaStatus} />
        <PaperPhaseEmpty
          icon={<Layers className="size-8" />}
          title="No structure yet"
          waiting={waitingOnPipeline}
          waitingDescription="Document understanding is still running. Abstract, sections, and method signals will appear here."
          idleDescription="Structure has not been extracted yet. Open Overview to start analysis when this manuscript is ready."
          onOpenOverview={() => navigate(`/papers/${fileId}`)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <AiStateBadge derived={derived} metaStatus={metaStatus} />
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          <FileText className="size-3.5" aria-hidden />
          Document understanding
        </span>
      </div>
      <StructureReady
        view={resolved}
        focusRef={focusRef}
        documentTypeLabel={documentTypeLabel}
      />
    </div>
  );
}
