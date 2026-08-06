import { useDeferredValue, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, Search, Tags } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { AiStateBadge, isPipelineError, usePipeline, usePipelinePhase } from "@/features/pipeline";
import { cn } from "@/lib/utils";
import { PaperPhaseEmpty } from "./PaperPhaseEmpty";
import {
  enrichEntitiesWithScientificProfile,
  filterClinicalGroups,
  filterEntityItems,
  filterPico,
  formatEntityConfidence,
  formatEntityLabel,
  mapEntities,
  type EntitiesViewModel,
  type EntityEvidenceView,
  type EntityItemView,
} from "../mappers/entities";
import { useWorkspaceFocus } from "../useWorkspaceFocus";

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
      {children}
    </h3>
  );
}

function EvidenceList({ evidence }: { evidence: EntityEvidenceView[] }) {
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
              ev.section ? formatEntityLabel(ev.section) : null,
              ev.page != null ? `p. ${ev.page}` : null,
              formatEntityConfidence(ev.confidence),
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </li>
      ))}
    </ul>
  );
}

function EntityCard({ item }: { item: EntityItemView }) {
  const confidenceText = formatEntityConfidence(item.confidence);
  const extraEntries = Object.entries(item.extras);
  const ariaLabel = [
    item.displayName,
    item.category ? formatEntityLabel(item.category) : null,
    confidenceText ? `confidence ${confidenceText}` : null,
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <article
      tabIndex={0}
      data-workspace-ref={item.key}
      aria-label={ariaLabel}
      className={cn(
        "rounded-xl border border-border bg-card p-3 outline-none",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
      )}
    >
      <header className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground break-words">{item.displayName}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {formatEntityLabel(item.category)}
          </p>
        </div>
        <p
          className="shrink-0 text-xs tabular-nums text-muted-foreground"
          aria-label={confidenceText ? `Confidence ${confidenceText}` : "Confidence unavailable"}
        >
          {confidenceText ?? "—"}
        </p>
      </header>

      {item.synonyms.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-1" role="list" aria-label="Synonyms">
          {item.synonyms.map((s) => (
            <li
              key={s}
              className="rounded-md border border-border bg-muted/40 px-1.5 py-0.5 text-[11px] text-foreground/85"
            >
              {s}
            </li>
          ))}
        </ul>
      )}

      {extraEntries.length > 0 && (
        <dl className="mt-2 space-y-0.5 text-xs text-foreground/80">
          {extraEntries.map(([k, v]) => (
            <div key={k} className="flex gap-2">
              <dt className="text-muted-foreground">{formatEntityLabel(k)}</dt>
              <dd className="min-w-0 break-words">{String(v)}</dd>
            </div>
          ))}
        </dl>
      )}

      <EvidenceList evidence={item.evidence} />
    </article>
  );
}

function ItemGrid({
  items,
  emptyLabel,
}: {
  items: EntityItemView[];
  emptyLabel?: string;
}) {
  if (items.length === 0) {
    return emptyLabel ? (
      <p className="text-sm text-muted-foreground">{emptyLabel}</p>
    ) : null;
  }
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {items.map((item) => (
        <EntityCard key={item.key} item={item} />
      ))}
    </div>
  );
}

function SummaryStrip({ view }: { view: EntitiesViewModel }) {
  const cells: [string, string][] = [
    ["Confidence", formatEntityConfidence(view.summary.overallConfidence) ?? "—"],
    ["Clinical entities", String(view.summary.clinicalEntityCount)],
    ["Scientific entities", String(view.summary.scientificEntityCount)],
    ["Interventions", String(view.summary.interventionCount)],
    ["Outcomes", String(view.summary.outcomeCount)],
  ];

  return (
    <section aria-labelledby="entities-summary-heading" className="space-y-2">
      <h2 id="entities-summary-heading" className="sr-only">
        Extraction summary
      </h2>
      <dl className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        {cells.map(([label, value]) => (
          <div
            key={label}
            className="rounded-xl border border-border bg-card px-3 py-2"
          >
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</dt>
            <dd className="mt-0.5 text-sm font-medium tabular-nums text-foreground">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function ScientificEntitiesSections({
  groups,
  relations,
  deferredQuery,
}: {
  groups: EntitiesViewModel["groups"]["scientificEntities"];
  relations: EntitiesViewModel["localRelations"];
  deferredQuery: string;
}) {
  const filteredGroups = filterClinicalGroups(groups, deferredQuery);
  const filteredRelations = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase();
    if (!q) return relations;
    return relations.filter(
      (r) =>
        r.subject.toLowerCase().includes(q) ||
        r.predicate.toLowerCase().includes(q) ||
        r.object.toLowerCase().includes(q),
    );
  }, [relations, deferredQuery]);

  if (!filteredGroups.length && !filteredRelations.length) return null;

  return (
    <>
      {filteredGroups.length > 0 && (
        <section aria-labelledby="entities-scientific-heading" className="space-y-4">
          <h2 id="entities-scientific-heading">
            <SectionHeading>Scientific entities</SectionHeading>
          </h2>
          <p className="text-[12px] text-muted-foreground">
            Paper-scoped signals from methodology and statistics (not a global knowledge graph).
          </p>
          {filteredGroups.map((group) => (
            <div key={group.entityType} className="space-y-2">
              <h3 className="text-sm font-medium text-foreground">
                {group.displayType}{" "}
                <span className="text-muted-foreground font-normal">({group.items.length})</span>
              </h3>
              <ItemGrid items={group.items} />
            </div>
          ))}
        </section>
      )}
      {filteredRelations.length > 0 && (
        <section aria-labelledby="entities-relations-heading" className="space-y-3">
          <h2 id="entities-relations-heading">
            <SectionHeading>Local relations</SectionHeading>
          </h2>
          <ul className="space-y-1.5 rounded-xl border border-border bg-card px-4 py-3 text-sm">
            {filteredRelations.map((r) => (
              <li key={r.key} className="text-foreground/90">
                <span className="font-medium">{r.subject}</span>
                <span className="mx-1.5 text-muted-foreground">{r.predicate}</span>
                <span className="font-medium">{r.object}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

function EntitiesReady({
  view,
  query,
  onQueryChange,
  focusRef,
}: {
  view: EntitiesViewModel;
  query: string;
  onQueryChange: (q: string) => void;
  focusRef?: string | null;
}) {
  useWorkspaceFocus(focusRef);
  const deferredQuery = useDeferredValue(query);

  const filtered = useMemo(() => {
    const clinical = filterClinicalGroups(view.groups.clinicalEntities, deferredQuery);
    const pico = filterPico(view.groups.pico, deferredQuery);
    return {
      clinical,
      pico,
      statistics: filterEntityItems(view.groups.statistics, deferredQuery),
      findings: filterEntityItems(view.groups.findings, deferredQuery),
      study: filterEntityItems(view.groups.studyCharacteristics, deferredQuery),
      temporal: filterEntityItems(view.groups.temporal, deferredQuery),
      scientific: filterClinicalGroups(view.groups.scientificEntities, deferredQuery),
    };
  }, [view, deferredQuery]);

  const picoHasItems =
    filtered.pico.populations.length +
      filtered.pico.interventions.length +
      filtered.pico.comparators.length +
      filtered.pico.outcomes.length >
    0;

  const hasScientific =
    view.groups.scientificEntities.length > 0 || view.localRelations.length > 0;

  const anyFiltered =
    filtered.clinical.length > 0 ||
    picoHasItems ||
    filtered.statistics.length > 0 ||
    filtered.findings.length > 0 ||
    filtered.study.length > 0 ||
    filtered.temporal.length > 0 ||
    filtered.scientific.length > 0;

  if (view.skipped && !hasScientific) {
    return (
      <div className="space-y-6">
        <SummaryStrip view={view} />
        <section
          aria-labelledby="entities-skipped-heading"
          className="rounded-xl border border-border bg-muted/20 px-4 py-5 space-y-2"
        >
          <h2 id="entities-skipped-heading" className="text-sm font-medium text-foreground">
            Medical extraction skipped
          </h2>
          <p className="text-sm text-foreground/85">
            {view.skipReason ??
              "This document was not routed through medical entity extraction."}
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

  return (
    <div className="space-y-8">
      <SummaryStrip view={view} />

      {view.skipped ? (
        <section
          aria-labelledby="entities-skipped-note"
          className="rounded-xl border border-border bg-muted/20 px-4 py-3"
        >
          <h2 id="entities-skipped-note" className="text-sm font-medium text-foreground">
            Medical extraction skipped
          </h2>
          <p className="mt-1 text-[13px] text-muted-foreground">
            {view.skipReason ??
              "Showing paper-scoped scientific entities from methodology and statistics instead."}
          </p>
        </section>
      ) : null}

      <div className="relative">
        <label htmlFor="entities-search" className="sr-only">
          Search entities and synonyms
        </label>
        <Search
          className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <input
          id="entities-search"
          type="search"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Search entities and synonyms…"
          className={cn(
            "w-full rounded-xl border border-border bg-card py-2.5 pl-9 pr-3 text-sm text-foreground",
            "placeholder:text-muted-foreground outline-none",
            "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          )}
        />
      </div>

      {deferredQuery.trim() && !anyFiltered && view.localRelations.length === 0 && (
        <p className="text-sm text-muted-foreground" role="status">
          No entities match “{deferredQuery.trim()}”.
        </p>
      )}

      <ScientificEntitiesSections
        groups={view.groups.scientificEntities}
        relations={view.localRelations}
        deferredQuery={deferredQuery}
      />

      {filtered.clinical.length > 0 && (
        <section aria-labelledby="entities-clinical-heading" className="space-y-4">
          <h2 id="entities-clinical-heading">
            <SectionHeading>Clinical entities</SectionHeading>
          </h2>
          {filtered.clinical.map((group) => (
            <div key={group.entityType} className="space-y-2">
              <h3 className="text-sm font-medium text-foreground">
                {group.displayType}{" "}
                <span className="text-muted-foreground font-normal">({group.items.length})</span>
              </h3>
              <ItemGrid items={group.items} />
            </div>
          ))}
        </section>
      )}

      {picoHasItems && (
        <section aria-labelledby="entities-pico-heading" className="space-y-4">
          <h2 id="entities-pico-heading">
            <SectionHeading>PICO</SectionHeading>
          </h2>
          {(
            [
              ["Populations", filtered.pico.populations],
              ["Interventions", filtered.pico.interventions],
              ["Comparators", filtered.pico.comparators],
              ["Outcomes", filtered.pico.outcomes],
            ] as const
          ).map(([label, items]) =>
            items.length ? (
              <div key={label} className="space-y-2">
                <h3 className="text-sm font-medium text-foreground">{label}</h3>
                <ItemGrid items={items} />
              </div>
            ) : null,
          )}
        </section>
      )}

      {filtered.statistics.length > 0 && (
        <section aria-labelledby="entities-stats-heading" className="space-y-2">
          <h2 id="entities-stats-heading">
            <SectionHeading>Statistics</SectionHeading>
          </h2>
          <ItemGrid items={filtered.statistics} />
        </section>
      )}

      {filtered.findings.length > 0 && (
        <section aria-labelledby="entities-findings-heading" className="space-y-2">
          <h2 id="entities-findings-heading">
            <SectionHeading>Key findings</SectionHeading>
          </h2>
          <ItemGrid items={filtered.findings} />
        </section>
      )}

      {filtered.study.length > 0 && (
        <section aria-labelledby="entities-study-heading" className="space-y-2">
          <h2 id="entities-study-heading">
            <SectionHeading>Study characteristics</SectionHeading>
          </h2>
          <ItemGrid items={filtered.study} />
        </section>
      )}

      {filtered.temporal.length > 0 && (
        <section aria-labelledby="entities-temporal-heading" className="space-y-2">
          <h2 id="entities-temporal-heading">
            <SectionHeading>Temporal</SectionHeading>
          </h2>
          <ItemGrid items={filtered.temporal} />
        </section>
      )}

      {view.warnings.length > 0 && (
        <section aria-labelledby="entities-warnings-heading" className="space-y-2">
          <h2 id="entities-warnings-heading">
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
        <section aria-labelledby="entities-errors-heading" className="space-y-2">
          <h2 id="entities-errors-heading">
            <SectionHeading>Extraction issues</SectionHeading>
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

      {!deferredQuery.trim() &&
        !anyFiltered &&
        view.warnings.length === 0 &&
        view.errors.length === 0 && (
          <p className="text-sm text-muted-foreground" role="status">
            No medical concepts were extracted for this paper.
          </p>
        )}
    </div>
  );
}

function EntitiesLoading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading entities">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-14 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-10 w-full rounded-xl" />
      <div className="grid gap-2 sm:grid-cols-2">
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
      </div>
    </div>
  );
}

/**
 * Entities tab — medical concepts + paper-scoped scientific entities (2.6).
 * Medical: GET …/phases/medical_understanding
 * Scientific: document_understanding.scientific_entities_profile
 */
export function PaperEntitiesTab({
  fileId,
  metaStatus,
  focusRef,
}: {
  fileId: number;
  metaStatus?: string | null;
  focusRef?: string | null;
}) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  const { pipeline, derived, isLoading: pipelineLoading, isError: pipelineError, error: pipelineErr } =
    usePipeline(fileId);

  const hasPhase =
    pipeline != null &&
    (pipeline.phases.includes("medical_understanding") ||
      "medical_understanding" in (pipeline.phase_results ?? {}));

  const hasDu =
    pipeline != null &&
    (pipeline.phases.includes("document_understanding") ||
      "document_understanding" in (pipeline.phase_results ?? {}));

  const phaseQuery = usePipelinePhase(fileId, "medical_understanding", {
    enabled: hasPhase,
  });
  const duQuery = usePipelinePhase(fileId, "document_understanding", {
    enabled: hasDu,
  });

  const view = useMemo(() => {
    const raw =
      phaseQuery.data?.result ?? pipeline?.phase_results?.medical_understanding ?? null;
    const medicalView = mapEntities(raw);
    const du =
      duQuery.data?.result ?? pipeline?.phase_results?.document_understanding ?? null;
    const profile =
      du && typeof du === "object" && du !== null && "scientific_entities_profile" in du
        ? (du as Record<string, unknown>).scientific_entities_profile
        : null;
    return enrichEntitiesWithScientificProfile(medicalView, profile);
  }, [phaseQuery.data, duQuery.data, pipeline]);

  const waitingOnPipeline =
    derived.isQueued ||
    derived.isRunning ||
    metaStatus === "pending" ||
    metaStatus === "running";

  const loading =
    pipelineLoading ||
    (hasPhase && phaseQuery.isLoading && !view) ||
    (hasDu && duQuery.isLoading && !view) ||
    (waitingOnPipeline && !view && !derived.isError);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <AiStateBadge derived={derived} metaStatus={metaStatus} />
        </div>
        <EntitiesLoading />
      </div>
    );
  }

  if (pipelineError || (hasPhase && phaseQuery.isError && !view)) {
    const err = phaseQuery.error ?? pipelineErr;
    const message = isPipelineError(err)
      ? err.code === "not_found"
        ? "Medical understanding is not available for this paper yet."
        : err.details || err.code
      : "Could not load entities.";
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
        <PaperPhaseEmpty
          icon={<Tags className="size-8" />}
          title="No entities yet"
          waiting={waitingOnPipeline}
          waitingDescription="Entity extraction is still running. Clinical and scientific signals will appear when ready."
          idleDescription="No entities extracted yet. Open Overview to start analysis when this manuscript is ready."
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
          <Tags className="size-3.5" aria-hidden />
          Entities
        </span>
      </div>
      <EntitiesReady view={view} query={query} onQueryChange={setQuery} focusRef={focusRef} />
    </div>
  );
}
