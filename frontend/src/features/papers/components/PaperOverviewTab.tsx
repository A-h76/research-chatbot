import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  MessageSquare,
  StickyNote,
  ArrowRight,
  Quote,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { UserFile } from "@/types/api";
import { useNotes } from "@/features/notes/useNotes";
import { usePipeline, usePipelinePhase } from "@/features/pipeline";
import { mapStructure } from "../mappers/structure";
import { mapClassification, profileDecisionLabel } from "../mappers/classification";
import {
  enrichEntitiesWithScientificProfile,
  mapEntities,
  formatEntityLabel,
} from "../mappers/entities";
import { mapEvidence, formatConfidence, formatLabel } from "../mappers/evidence";
import { mapKnowledgeGraph } from "../mappers/graph";
import type { PaperTabId } from "../tabs";
import { PaperStatStrip } from "./PaperStatStrip";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
      {children}
    </p>
  );
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (value == null || value === "") return null;
  return (
    <div className="grid grid-cols-[6.5rem_1fr] gap-2 py-1 text-[13px] sm:grid-cols-[7.5rem_1fr]">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words text-foreground">{value}</dd>
    </div>
  );
}

/** D4 — Overview = Summary → compact signals → actions (paper is the hero). */
export function PaperOverviewTab({
  file,
  fileId,
  onChat,
  onCite,
  citePending,
  chatPending,
  onJumpTab,
}: {
  file: UserFile;
  fileId: number;
  onChat: () => void;
  onCite: () => void;
  citePending: boolean;
  chatPending: boolean;
  onJumpTab: (tab: PaperTabId) => void;
}) {
  const navigate = useNavigate();
  const { data: notesData, isLoading: notesLoading } = useNotes({ file_id: fileId });
  const notes = notesData?.items ?? [];

  const { pipeline, isLoading: pipelineLoading } = usePipeline(fileId);
  const has = (phase: string) =>
    pipeline != null &&
    (pipeline.phases.includes(phase as never) || phase in (pipeline.phase_results ?? {}));

  const duQ = usePipelinePhase(fileId, "document_understanding", {
    enabled: has("document_understanding"),
  });
  const clfQ = usePipelinePhase(fileId, "classification", { enabled: has("classification") });
  const ctxQ = usePipelinePhase(fileId, "analysis_context", { enabled: has("analysis_context") });
  const medQ = usePipelinePhase(fileId, "medical_understanding", {
    enabled: has("medical_understanding"),
  });
  const egQ = usePipelinePhase(fileId, "evidence_grading", { enabled: has("evidence_grading") });
  const kgQ = usePipelinePhase(fileId, "knowledge_graph", { enabled: has("knowledge_graph") });

  const summary = useMemo(() => {
    const structure = mapStructure(
      duQ.data?.result ?? pipeline?.phase_results?.document_understanding ?? null,
    );
    const classification = mapClassification(
      clfQ.data?.result ?? pipeline?.phase_results?.classification ?? null,
      ctxQ.data?.result ?? pipeline?.phase_results?.analysis_context ?? null,
    );
    const entities = enrichEntitiesWithScientificProfile(
      mapEntities(medQ.data?.result ?? pipeline?.phase_results?.medical_understanding ?? null),
      (
        (duQ.data?.result ?? pipeline?.phase_results?.document_understanding) as
          | Record<string, unknown>
          | null
          | undefined
      )?.scientific_entities_profile,
    );
    const evidence = mapEvidence(
      egQ.data?.result ?? pipeline?.phase_results?.evidence_grading ?? null,
    );
    const graph = mapKnowledgeGraph(
      kgQ.data?.result ?? pipeline?.phase_results?.knowledge_graph ?? null,
    );
    return { structure, classification, entities, evidence, graph };
  }, [pipeline, duQ.data, clfQ.data, ctxQ.data, medQ.data, egQ.data, kgQ.data]);

  const loadingPhases =
    pipelineLoading ||
    (has("document_understanding") && duQ.isLoading) ||
    (has("classification") && clfQ.isLoading) ||
    (has("medical_understanding") && medQ.isLoading) ||
    (has("evidence_grading") && egQ.isLoading) ||
    (has("knowledge_graph") && kgQ.isLoading);

  const { structure, classification, entities, evidence, graph } = summary;

  const studyType = classification?.decisions.find((d) => d.family === "document_type");
  const studyDesign = classification?.decisions.find((d) => d.family === "study_design");
  const domain = classification?.decisions.find((d) => d.family === "domain");

  const topEntities = entities
    ? [
        ...(!entities.skipped
          ? [
              ...entities.groups.clinicalEntities.flatMap((g) => g.items),
              ...entities.groups.pico.interventions,
              ...entities.groups.pico.outcomes,
            ]
          : []),
        ...entities.groups.scientificEntities.flatMap((g) => g.items),
      ].slice(0, 6)
    : [];

  const journal = structure?.journal || structure?.venue || file.venue || undefined;
  const year = structure?.publicationYear ?? file.year ?? undefined;
  const authors = structure?.authors?.length
    ? structure.authors.join("; ")
    : file.authors || undefined;
  const abstractText = structure?.abstract || file.abstract || "";

  const entityCount = entities
    ? (entities.skipped ? 0 : entities.summary.clinicalEntityCount) +
      entities.summary.scientificEntityCount +
      (entities.skipped
        ? 0
        : entities.summary.interventionCount + entities.summary.outcomeCount)
    : null;

  const peers = classification?.decisions ?? [];
  const studyTypeLabel = studyType ? profileDecisionLabel(studyType, peers) : null;
  const studyDesignLabel = studyDesign ? profileDecisionLabel(studyDesign, peers) : null;
  const domainLabel = domain ? profileDecisionLabel(domain, peers) : null;
  const studyTypeShow =
    studyTypeLabel && studyTypeLabel !== "Not identified" && studyTypeLabel !== "Not applicable"
      ? studyTypeLabel
      : null;
  const domainShow =
    domainLabel && domainLabel !== "Not identified" && domainLabel !== "Not applicable"
      ? domainLabel
      : null;
  const studyDesignShow =
    studyDesignLabel &&
    studyDesignLabel !== "Not identified" &&
    studyDesignLabel !== "Not applicable"
      ? studyDesignLabel
      : null;

  const evidenceSkipped = Boolean(evidence?.skipped);
  const evidenceGrade =
    evidence?.overallGrade?.displayValue ??
    (evidence?.studyQuality && evidence.studyQuality !== "unknown"
      ? formatLabel(evidence.studyQuality)
      : null);
  const evidenceLabel = evidenceSkipped
    ? "Not Assessed"
    : evidenceGrade ?? (evidence?.hasContent ? "Not Assessed" : null);
  const evidenceHint = evidenceSkipped
    ? evidence?.skipReason ?? "Open Evidence for why"
    : evidence?.summaryConfidence != null
      ? formatConfidence(evidence.summaryConfidence)
      : evidenceGrade
        ? undefined
        : evidence?.skipReason ?? "No formal grade yet";

  return (
    <div className="space-y-5">
      {/* 1. Summary — paper is the hero */}
      {(abstractText || studyTypeShow || domainShow) && (
        <section aria-labelledby="overview-summary-heading">
          <SectionLabel>Summary</SectionLabel>
          <div className="rounded-lg border border-border bg-card px-4 py-3 space-y-2">
            {(studyTypeShow || domainShow) && (
              <p className="text-[13px] text-muted-foreground">
                {[studyTypeShow, domainShow, studyDesignShow].filter(Boolean).join(" · ")}
              </p>
            )}
            {abstractText ? (
              <p className="text-[14px] leading-relaxed text-foreground/90 line-clamp-6">
                {abstractText}
              </p>
            ) : (
              <p className="text-[13px] text-muted-foreground">No abstract extracted yet.</p>
            )}
          </div>
        </section>
      )}

      {/* 2. Compact signals */}
      {loadingPhases && !classification && !evidence && !entities ? (
        <Skeleton className="h-4 w-64" aria-busy="true" />
      ) : (
        <PaperStatStrip
          evidenceLabel={evidenceLabel}
          evidenceHint={evidenceHint}
          entityCount={entityCount}
          entitySkipped={Boolean(entities?.skipped && !entities.summary.scientificEntityCount)}
          graphNodes={graph && !graph.skipped ? graph.summary.nodeCount : null}
          graphEdges={graph && !graph.skipped ? graph.summary.edgeCount : null}
          classificationLabel={domainShow ?? studyTypeShow ?? null}
          classificationHint={
            [studyDesignShow, studyTypeShow].filter(Boolean).join(" · ") || null
          }
          onJump={onJumpTab}
        />
      )}

      {/* 3. Actions */}
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={onChat} disabled={chatPending} size="sm" className="gap-1.5">
          <MessageSquare className="size-3.5" />
          Ask about this paper
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={onCite}
          disabled={citePending || !file.title}
          className="gap-1.5"
          title={!file.title ? "Metadata extraction pending" : "Save to citations"}
        >
          <Quote className="size-3.5" />
          Cite
        </Button>
        <button
          type="button"
          onClick={() => onJumpTab("evidence")}
          className="text-[12px] text-muted-foreground hover:text-foreground"
        >
          Open Evidence →
        </button>
      </div>

      {/* 3b. Scientific framing (2.1) — structured, not Narrative LLM */}
      {structure?.scientificStructure &&
        (structure.scientificStructure.objectives.length > 0 ||
          structure.scientificStructure.researchQuestions.length > 0 ||
          structure.scientificStructure.hypotheses.length > 0 ||
          structure.scientificStructure.problemStatement) && (
          <section aria-labelledby="overview-framing-heading">
            <SectionLabel>Scientific framing</SectionLabel>
            <div className="space-y-2 rounded-lg border border-border bg-card px-4 py-3">
              {structure.scientificStructure.problemStatement ? (
                <p className="text-[13px] leading-relaxed text-foreground/90">
                  <span className="font-medium text-muted-foreground">Problem · </span>
                  {structure.scientificStructure.problemStatement.text}
                </p>
              ) : null}
              {structure.scientificStructure.objectives.slice(0, 2).map((o, i) => (
                <p key={`obj-${i}`} className="text-[13px] leading-relaxed text-foreground/90">
                  <span className="font-medium text-muted-foreground">Objective · </span>
                  {o.text}
                </p>
              ))}
              {structure.scientificStructure.researchQuestions.slice(0, 2).map((q, i) => (
                <p key={`rq-${i}`} className="text-[13px] leading-relaxed text-foreground/90">
                  <span className="font-medium text-muted-foreground">Question · </span>
                  {q.text}
                </p>
              ))}
              {structure.scientificStructure.hypotheses.slice(0, 1).map((h, i) => (
                <p key={`hyp-${i}`} className="text-[13px] leading-relaxed text-foreground/90">
                  <span className="font-medium text-muted-foreground">Hypothesis · </span>
                  {h.text}
                </p>
              ))}
              <button
                type="button"
                onClick={() => onJumpTab("structure")}
                className="text-[12px] text-primary hover:underline"
              >
                Open Structure →
              </button>
            </div>
          </section>
        )}

      {/* 3c. Method + Evaluation hints (Sprint 3) */}
      {structure?.methodologyProfile?.hasContent && (
        <>
          {(structure.methodologyProfile.studyDesign ||
            structure.methodologyProfile.sampleSize ||
            structure.methodologyProfile.population ||
            structure.methodologyProfile.dataset ||
            structure.methodologyProfile.experimentalSetup) && (
            <section aria-labelledby="overview-method-heading">
              <SectionLabel>Method</SectionLabel>
              <div className="space-y-2 rounded-lg border border-border bg-card px-4 py-3">
                {structure.methodologyProfile.studyDesign ? (
                  <p className="text-[13px] leading-relaxed text-foreground/90">
                    <span className="font-medium text-muted-foreground">Design · </span>
                    {structure.methodologyProfile.studyDesign.label?.replace(/_/g, " ") ||
                      structure.methodologyProfile.studyDesign.text}
                  </p>
                ) : null}
                {structure.methodologyProfile.sampleSize ? (
                  <p className="text-[13px] leading-relaxed text-foreground/90">
                    <span className="font-medium text-muted-foreground">Sample · </span>
                    {structure.methodologyProfile.sampleSize.text}
                  </p>
                ) : null}
                {structure.methodologyProfile.population ? (
                  <p className="text-[13px] leading-relaxed text-foreground/90">
                    <span className="font-medium text-muted-foreground">Population · </span>
                    {structure.methodologyProfile.population.text}
                  </p>
                ) : null}
                {structure.methodologyProfile.dataset &&
                !structure.methodologyProfile.population ? (
                  <p className="text-[13px] leading-relaxed text-foreground/90">
                    <span className="font-medium text-muted-foreground">Dataset · </span>
                    {structure.methodologyProfile.dataset.text}
                  </p>
                ) : null}
                {structure.methodologyProfile.experimentalSetup ? (
                  <p className="text-[13px] leading-relaxed text-foreground/90">
                    <span className="font-medium text-muted-foreground">Setup · </span>
                    {structure.methodologyProfile.experimentalSetup.text}
                  </p>
                ) : null}
                <button
                  type="button"
                  onClick={() => onJumpTab("structure")}
                  className="text-[12px] text-primary hover:underline"
                >
                  Open Structure →
                </button>
              </div>
            </section>
          )}
          {structure.methodologyProfile.metrics.length > 0 && (
            <section aria-labelledby="overview-evaluation-heading">
              <SectionLabel>Evaluation</SectionLabel>
              <div className="space-y-2 rounded-lg border border-border bg-card px-4 py-3">
                <p className="text-[13px] leading-relaxed text-foreground/90">
                  <span className="font-medium text-muted-foreground">Metrics · </span>
                  {structure.methodologyProfile.metrics
                    .slice(0, 4)
                    .map((m) => m.label?.replace(/_/g, " ") || m.text)
                    .join(", ")}
                </p>
                <button
                  type="button"
                  onClick={() => onJumpTab("structure")}
                  className="text-[12px] text-primary hover:underline"
                >
                  Open Structure →
                </button>
              </div>
            </section>
          )}
        </>
      )}

      {/* 3d. Statistical findings hint (2.3) */}
      {structure?.statisticsProfile?.hasContent && (
        <section aria-labelledby="overview-stats-findings-heading">
          <SectionLabel>Statistical findings</SectionLabel>
          <div className="space-y-2 rounded-lg border border-border bg-card px-4 py-3">
            {structure.statisticsProfile.tests.slice(0, 2).map((t, i) => (
              <p key={`test-${i}`} className="text-[13px] leading-relaxed text-foreground/90">
                <span className="font-medium text-muted-foreground">Test · </span>
                {t.label?.replace(/_/g, " ") || t.text}
              </p>
            ))}
            {structure.statisticsProfile.pValues.slice(0, 2).map((p, i) => (
              <p key={`p-${i}`} className="text-[13px] leading-relaxed text-foreground/90">
                <span className="font-medium text-muted-foreground">P · </span>
                {p.text}
              </p>
            ))}
            {structure.statisticsProfile.effectSizes.slice(0, 2).map((e, i) => (
              <p key={`es-${i}`} className="text-[13px] leading-relaxed text-foreground/90">
                <span className="font-medium text-muted-foreground">Effect · </span>
                {e.text}
              </p>
            ))}
            {structure.statisticsProfile.interpretations.slice(0, 1).map((interp, i) => (
              <p key={`interp-${i}`} className="text-[13px] leading-relaxed text-foreground/90">
                <span className="font-medium text-muted-foreground">Author · </span>
                {interp.text}
              </p>
            ))}
            <button
              type="button"
              onClick={() => onJumpTab("structure")}
              className="text-[12px] text-primary hover:underline"
            >
              Open Structure →
            </button>
          </div>
        </section>
      )}

      {/* 3e. Limitations & novelty hint (2.5) */}
      {structure?.limitationsNoveltyProfile?.hasContent && (
        <section aria-labelledby="overview-limitations-novelty-heading">
          <SectionLabel>Limitations &amp; novelty</SectionLabel>
          <div className="space-y-2 rounded-lg border border-border bg-card px-4 py-3">
            {structure.limitationsNoveltyProfile.limitations.slice(0, 2).map((item, i) => (
              <p key={`lim-${i}`} className="text-[13px] leading-relaxed text-foreground/90">
                <span className="font-medium text-muted-foreground">Limitation · </span>
                {item.text}
              </p>
            ))}
            {structure.limitationsNoveltyProfile.novelty.slice(0, 2).map((item, i) => (
              <p key={`nov-${i}`} className="text-[13px] leading-relaxed text-foreground/90">
                <span className="font-medium text-muted-foreground">Novelty · </span>
                {item.text}
              </p>
            ))}
            {structure.limitationsNoveltyProfile.futureWork.slice(0, 1).map((item, i) => (
              <p key={`fut-${i}`} className="text-[13px] leading-relaxed text-foreground/90">
                <span className="font-medium text-muted-foreground">Future · </span>
                {item.text}
              </p>
            ))}
            <button
              type="button"
              onClick={() => onJumpTab("structure")}
              className="text-[12px] text-primary hover:underline"
            >
              Open Structure →
            </button>
          </div>
        </section>
      )}

      {/* 3f. Quality assessment hint (2.7) */}
      {structure?.qualityAssessment?.hasContent && (
        <section aria-labelledby="overview-quality-heading">
          <SectionLabel>Quality assessment</SectionLabel>
          <div className="space-y-2 rounded-lg border border-border bg-card px-4 py-3">
            {structure.qualityAssessment.sections.slice(0, 4).map((section) => {
              const top = section.items.find((i) => i.status === "pass") || section.items[0];
              return (
                <p key={section.id} className="text-[13px] leading-relaxed text-foreground/90">
                  <span className="font-medium text-muted-foreground">
                    {section.label} · {section.band} ·{" "}
                  </span>
                  {top ? `${top.status === "pass" ? "✓" : top.status === "missing" ? "—" : "•"} ${top.text}` : "—"}
                </p>
              );
            })}
            <p className="text-[11px] text-muted-foreground">
              Checklist with reasons — not an opaque score.
            </p>
            <button
              type="button"
              onClick={() => onJumpTab("structure")}
              className="text-[12px] text-primary hover:underline"
            >
              Open Structure →
            </button>
          </div>
        </section>
      )}

      {/* 4. Top entities */}
      {topEntities.length > 0 && (
        <section>
          <SectionLabel>Key entities</SectionLabel>
          <ul className="flex flex-wrap gap-1.5" role="list">
            {topEntities.map((item) => (
              <li key={item.key}>
                <button
                  type="button"
                  onClick={() => onJumpTab("entities")}
                  className="inline-flex max-w-full items-center rounded-md border border-border bg-card px-2 py-0.5 text-xs hover:bg-muted/50"
                  title={formatEntityLabel(item.category)}
                >
                  <span className="truncate">{item.displayName}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* 5. Compact document meta */}
      <section aria-labelledby="overview-doc-heading">
        <SectionLabel>Document</SectionLabel>
        <dl className="rounded-lg border border-border bg-card px-4 py-2">
          <MetaRow label="Title" value={file.title || file.name} />
          <MetaRow label="Authors" value={authors} />
          <MetaRow label="Journal" value={journal} />
          <MetaRow label="Year" value={year} />
          <MetaRow
            label="Sections"
            value={
              structure?.sections?.length ? (
                <button
                  type="button"
                  onClick={() => onJumpTab("structure")}
                  className="text-primary hover:underline"
                >
                  {structure.sections.length} detected
                </button>
              ) : null
            }
          />
        </dl>
      </section>

      {file.tags?.length > 0 && (
        <section>
          <SectionLabel>Tags</SectionLabel>
          <div className="flex flex-wrap gap-1.5">
            {file.tags.map((t) => (
              <Badge key={t} variant="secondary" className="text-xs">
                {t}
              </Badge>
            ))}
          </div>
        </section>
      )}

      {/* 6. Notes — compact */}
      <section>
        <SectionLabel>Notes</SectionLabel>
        {notesLoading ? (
          <Skeleton className="h-9 w-full rounded-lg" />
        ) : notes.length === 0 ? (
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-dashed border-border px-3 py-2">
            <p className="text-[13px] text-muted-foreground">No notes yet.</p>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 gap-1 text-[12px]"
              onClick={() => navigate(`/notes?file_id=${fileId}`)}
            >
              <StickyNote className="size-3.5" />
              Add note
            </Button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => navigate(`/notes?file_id=${fileId}`)}
            className="flex w-full items-center justify-between rounded-lg border border-border bg-card px-3 py-2 text-left hover:bg-muted/40"
          >
            <span className="text-[13px]">
              {notes.length} note{notes.length === 1 ? "" : "s"}
            </span>
            <span className="inline-flex items-center gap-1 text-[12px] text-primary">
              View <ArrowRight className="size-3" />
            </span>
          </button>
        )}
      </section>
    </div>
  );
}
