import { useEffect, useMemo, useState } from "react";
import { AlertCircle, ChevronDown, ChevronRight, FileText, Layers } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { AiStateBadge, isPipelineError, usePipeline, usePipelinePhase } from "@/features/pipeline";
import { cn } from "@/lib/utils";
import {
  mapStructure,
  type DocumentUnderstandingView,
} from "../mappers/structure";
import { mapClassification } from "../mappers/classification";
import { structureSectionRefId } from "../mappers/chat";
import { useWorkspaceFocus } from "../useWorkspaceFocus";
import { parseSectionBody } from "./sectionContent";
import { buildDocumentAnalysisReport } from "./documentAnalysis";
import { DocumentAnalysisPanel } from "./DocumentAnalysisPanel";

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
      {children}
    </h3>
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
                      <span className="mt-0.5 flex flex-wrap gap-2 text-xs text-muted-foreground">
                        {sec.sectionType && (
                          <span className="rounded-full border border-border px-2 py-0.5">
                            {sec.sectionType}
                          </span>
                        )}
                        {sec.contentChars != null && (
                          <span>{sec.contentChars.toLocaleString()} characters</span>
                        )}
                      </span>
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
  const { pipeline, derived, isLoading: pipelineLoading, isError: pipelineError, error: pipelineErr } =
    usePipeline(fileId);

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
        <EmptyState
          icon={<Layers className="size-8" />}
          title="No structure yet"
          description={
            waitingOnPipeline
              ? "Document understanding is still running. This tab will fill in when the phase completes."
              : "No document_understanding result is available for this paper. Run Phase 1 analysis to extract structure."
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
