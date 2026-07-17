import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  GitCompare, Loader2, RefreshCw, CheckCircle2, ChevronDown, ChevronUp,
  AlertTriangle, Lightbulb, ArrowRight, FileText, Zap, SearchX,
  BookOpen, FlaskConical, HelpCircle, Database, GraduationCap,
} from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button }        from "@/components/ui/button";
import { Badge }         from "@/components/ui/badge";
import { Skeleton }      from "@/components/ui/skeleton";
import { Separator }     from "@/components/ui/separator";
import { EmptyState }    from "@/components/common/EmptyState";
import { useAllFiles }   from "@/features/files/useFiles";
import {
  useCompare, useComparison,
  useFindGaps, useGapResult,
} from "../useAnalysis";
import { useUI }         from "@/context/UIContext";
import { toast }         from "@/components/common/Toast";
import { cn }            from "@/lib/utils";
import type { ComparisonData, GapFinderData, UserFile } from "@/types/api";

// ─── Shared: Paper picker chip ───────────────────────────────────────────────
function PaperChip({
  file, selected, onToggle,
}: { file: UserFile; selected: boolean; onToggle: () => void }) {
  const title = file.title || file.name;
  return (
    <button
      onClick={onToggle}
      className={cn(
        "flex items-center gap-2.5 rounded-xl border px-3 py-2.5 text-left text-sm transition-all",
        selected
          ? "border-primary bg-accent-soft text-primary shadow-sm"
          : "border-border bg-card hover:border-primary/40 hover:bg-muted/50",
      )}
    >
      <div className={cn(
        "flex size-6 shrink-0 items-center justify-center rounded-md transition-colors",
        selected ? "bg-primary text-primary-foreground" : "bg-muted",
      )}>
        {selected
          ? <CheckCircle2 className="size-3.5" />
          : <FileText className="size-3.5 text-muted-foreground" />}
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium" title={title}>
          {title.length > 45 ? title.slice(0, 45) + "…" : title}
        </p>
        {(file.authors || file.year) && (
          <p className="truncate text-xs text-muted-foreground">
            {[file.authors?.split(";")[0]?.trim(), file.year]
              .filter(Boolean).join(" · ")}
          </p>
        )}
      </div>
    </button>
  );
}

// ─── Shared: Collapsible section ─────────────────────────────────────────────
function ResultSection({
  icon, title, children, defaultOpen = true,
}: {
  icon: React.ReactNode; title: string;
  children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2.5 px-4 py-3 text-left hover:bg-muted/40 transition-colors"
      >
        <span className="text-primary">{icon}</span>
        <span className="flex-1 text-sm font-semibold">{title}</span>
        {open
          ? <ChevronUp className="size-4 text-muted-foreground" />
          : <ChevronDown className="size-4 text-muted-foreground" />}
      </button>
      {open && (
        <div className="border-t border-border px-4 pb-4 pt-3">
          {children}
        </div>
      )}
    </div>
  );
}

function BulletList({ items }: { items?: string[] }) {
  if (!items?.length)
    return <p className="text-sm text-muted-foreground italic">None identified.</p>;
  return (
    <ul className="space-y-2">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-foreground/90">
          <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary/60" />
          <span className="leading-relaxed">{item}</span>
        </li>
      ))}
    </ul>
  );
}

function LoadingSkeleton({ label }: { label: string }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        {label}
      </div>
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-24 rounded-2xl" />
      ))}
    </div>
  );
}

// ─── Tab: Comparison results ─────────────────────────────────────────────────
function CompareResults({
  data, onRefresh, isRefreshing,
}: { data: ComparisonData; onRefresh: () => void; isRefreshing: boolean }) {
  if (data.error)
    return (
      <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-5">
        <p className="font-medium text-destructive">Analysis failed</p>
        <p className="mt-1 text-sm text-muted-foreground">{data.error}</p>
        <Button size="sm" variant="outline" className="mt-3 gap-2"
                onClick={onRefresh} disabled={isRefreshing}>
          <RefreshCw className={cn("size-4", isRefreshing && "animate-spin")} />
          Retry
        </Button>
      </div>
    );

  return (
    <div className="space-y-4">
      {data.overview && (
        <div className="rounded-2xl border border-primary/20 bg-accent-soft/60 p-4">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-primary">Overview</p>
          <p className="text-sm leading-relaxed">{data.overview}</p>
        </div>
      )}

      {data.methodologies && Object.keys(data.methodologies).length > 0 && (
        <ResultSection icon={<FileText className="size-4" />} title="Methodology by Paper">
          <dl className="space-y-3">
            {Object.entries(data.methodologies).map(([t, m]) => (
              <div key={t}>
                <dt className="text-xs font-semibold">{t}</dt>
                <dd className="mt-0.5 text-sm text-muted-foreground leading-relaxed">{m}</dd>
              </div>
            ))}
          </dl>
        </ResultSection>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <ResultSection icon={<CheckCircle2 className="size-4" />} title="Similarities">
          <BulletList items={data.similarities} />
        </ResultSection>
        <ResultSection icon={<GitCompare className="size-4" />} title="Differences">
          <BulletList items={data.differences} />
        </ResultSection>
        <ResultSection icon={<CheckCircle2 className="size-4" />} title="Agreements">
          <BulletList items={data.agreements} />
        </ResultSection>
        <ResultSection icon={<AlertTriangle className="size-4" />} title="Contradictions" defaultOpen={false}>
          <BulletList items={data.contradictions} />
        </ResultSection>
      </div>

      {(data.common_datasets?.length ?? 0) > 0 && (
        <ResultSection icon={<Zap className="size-4" />} title="Common Datasets">
          <div className="flex flex-wrap gap-2">
            {data.common_datasets!.map((ds) => (
              <Badge key={ds} variant="outline" className="text-xs font-normal">{ds}</Badge>
            ))}
          </div>
        </ResultSection>
      )}

      {(data.research_trends?.length ?? 0) > 0 && (
        <ResultSection icon={<ArrowRight className="size-4" />} title="Research Trends">
          <BulletList items={data.research_trends} />
        </ResultSection>
      )}

      {data.synthesis && (
        <ResultSection icon={<Lightbulb className="size-4" />} title="Synthesis">
          <p className="text-sm leading-relaxed text-foreground/90">{data.synthesis}</p>
        </ResultSection>
      )}

      <div className="flex justify-end pt-1">
        <Button size="sm" variant="ghost" className="gap-2 text-muted-foreground"
                onClick={onRefresh} disabled={isRefreshing}>
          <RefreshCw className={cn("size-3.5", isRefreshing && "animate-spin")} />
          Re-analyse
        </Button>
      </div>
    </div>
  );
}

// ─── Tab: Gap finder results ─────────────────────────────────────────────────
function GapResults({
  data, onRefresh, isRefreshing,
}: { data: GapFinderData; onRefresh: () => void; isRefreshing: boolean }) {
  if (data.error)
    return (
      <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-5">
        <p className="font-medium text-destructive">Analysis failed</p>
        <p className="mt-1 text-sm text-muted-foreground">{data.error}</p>
        <Button size="sm" variant="outline" className="mt-3 gap-2"
                onClick={onRefresh} disabled={isRefreshing}>
          <RefreshCw className={cn("size-4", isRefreshing && "animate-spin")} /> Retry
        </Button>
      </div>
    );

  return (
    <div className="space-y-4">
      {/* AI disclaimer banner — always prominent */}
      <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3.5 dark:border-amber-800 dark:bg-amber-950/40">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" />
        <p className="text-xs leading-relaxed text-amber-800 dark:text-amber-300">
          {data.disclaimer ??
            "These are AI-generated suggestions. Treat them as starting points for your own critical assessment."}
        </p>
      </div>

      {data.preamble && (
        <div className="rounded-2xl border border-primary/20 bg-accent-soft/60 p-4">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-primary">Field overview</p>
          <p className="text-sm leading-relaxed">{data.preamble}</p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <ResultSection icon={<SearchX className="size-4" />} title="Underexplored Topics">
          <BulletList items={data.underexplored_topics} />
        </ResultSection>

        <ResultSection icon={<FlaskConical className="size-4" />} title="Missing Experiments">
          <BulletList items={data.missing_experiments} />
        </ResultSection>

        <ResultSection icon={<HelpCircle className="size-4" />} title="Open Questions">
          <BulletList items={data.open_questions} />
        </ResultSection>

        <ResultSection icon={<AlertTriangle className="size-4" />} title="Methodological Gaps" defaultOpen={false}>
          <BulletList items={data.methodological_gaps} />
        </ResultSection>

        <ResultSection icon={<Database className="size-4" />} title="Dataset Gaps" defaultOpen={false}>
          <BulletList items={data.dataset_gaps} />
        </ResultSection>

        <ResultSection icon={<GraduationCap className="size-4" />} title="Potential Thesis Ideas">
          <BulletList items={data.potential_thesis_ideas} />
        </ResultSection>
      </div>

      {(data.future_opportunities?.length ?? 0) > 0 && (
        <ResultSection icon={<BookOpen className="size-4" />} title="Future Research Opportunities">
          <BulletList items={data.future_opportunities} />
        </ResultSection>
      )}

      <div className="flex justify-end pt-1">
        <Button size="sm" variant="ghost" className="gap-2 text-muted-foreground"
                onClick={onRefresh} disabled={isRefreshing}>
          <RefreshCw className={cn("size-3.5", isRefreshing && "animate-spin")} />
          Re-analyse
        </Button>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
type ActiveTab = "compare" | "gaps";

export function MultiPaperAnalysisPage() {
  const { currentProjectId } = useUI();
  const { data: allFilesRaw } = useAllFiles();
  // Only show papers with completed analyses
  const allFiles = (allFilesRaw ?? []).filter(
    (f) => f.kind === "document" && f.meta_status === "done",
  );

  const [activeTab, setActiveTab] = useState<ActiveTab>("compare");
  const [selected,  setSelected]  = useState<number[]>([]);
  const [searchQ,   setSearchQ]   = useState("");

  // Compare state
  const [compId,  setCompId]  = useState<number | null>(null);
  const compare               = useCompare();
  const { data: compResult, isLoading: compLoading } = useComparison(compId);

  // Gaps state
  const [gapsId,  setGapsId]  = useState<number | null>(null);
  const findGaps              = useFindGaps();
  const { data: gapsResult, isLoading: gapsLoading } = useGapResult(gapsId);

  const filtered = searchQ.trim()
    ? allFiles.filter((f) => {
        const hay = [f.title, f.name, f.authors, f.year].join(" ").toLowerCase();
        return hay.includes(searchQ.toLowerCase());
      })
    : allFiles;

  function toggleFile(id: number) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  async function run(force = false) {
    if (selected.length < 2) { toast.error("Select at least 2 papers."); return; }

    const input = { file_ids: selected, project_id: currentProjectId, force };

    try {
      if (activeTab === "compare") {
        const r = await compare.mutateAsync(input);
        if (r.skipped?.length) {
          toast.warning(`Skipped (no analysis yet): ${r.skipped.map((s) => s.name ?? `#${s.id}`).join(", ")}`);
        }
        setCompId(r.id);
      } else {
        const r = await findGaps.mutateAsync(input);
        if (r.skipped?.length) {
          toast.warning(`Skipped (no analysis yet): ${r.skipped.map((s) => s.name ?? `#${s.id}`).join(", ")}`);
        }
        setGapsId(r.id);
      }
    } catch {
      toast.error("Could not start analysis.");
    }
  }

  const isPending  = activeTab === "compare" ? compare.isPending  : findGaps.isPending;
  const isRunning  = isPending || (activeTab === "compare"
    ? compResult?.status === "running"
    : gapsResult?.status === "running");

  const currentId     = activeTab === "compare" ? compId  : gapsId;
  const currentResult = activeTab === "compare" ? compResult : gapsResult;
  const currentLoading= activeTab === "compare" ? compLoading : gapsLoading;
  const isDone        = currentResult?.status === "done";

  const TABS: { key: ActiveTab; label: string; desc: string }[] = [
    {
      key:   "compare",
      label: "Compare Papers",
      desc:  "Similarities, differences, contradictions, and synthesis across your selection.",
    },
    {
      key:   "gaps",
      label: "Research Gaps",
      desc:  "Underexplored topics, missing experiments, open questions, and thesis ideas.",
    },
  ];

  return (
    <PageContainer
      title="Multi-Paper Analysis"
      description="Select 2–10 analysed papers to run a comparison or identify research gaps."
    >
      <div className="space-y-6">

        {/* ── Tab bar ── */}
        <div className="flex items-center gap-1 rounded-xl border border-border bg-muted/40 p-1">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                "flex-1 rounded-lg px-4 py-2 text-sm font-medium transition-all",
                activeTab === tab.key
                  ? "bg-card shadow-sm text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab description */}
        <p className="text-sm text-muted-foreground -mt-2">
          {TABS.find((t) => t.key === activeTab)?.desc}
        </p>

        {/* ── Paper picker ── */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">
              Select papers
              {selected.length > 0 && (
                <span className="ml-2 rounded-full bg-primary/15 px-2 py-0.5 text-xs text-primary">
                  {selected.length} selected
                </span>
              )}
            </h2>
            {selected.length > 0 && (
              <button
                onClick={() => setSelected([])}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Clear
              </button>
            )}
          </div>

          <input
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            placeholder="Filter papers…"
            className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:border-ring"
          />

          {allFiles.length === 0 ? (
            <EmptyState
              icon={<FileText className="size-8" />}
              title="No analysed papers yet"
              description="Upload papers and wait for their analysis to complete before running a comparison."
            />
          ) : filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground">No papers match your filter.</p>
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <AnimatePresence>
                {filtered.map((f) => (
                  <motion.div
                    key={f.id}
                    initial={{ opacity: 0, scale: 0.97 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.12 }}
                  >
                    <PaperChip
                      file={f}
                      selected={selected.includes(f.id)}
                      onToggle={() => toggleFile(f.id)}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </section>

        {/* ── Run button ── */}
        <div className="flex items-center gap-3">
          <Button
            onClick={() => run(false)}
            disabled={selected.length < 2 || isRunning}
            className="gap-2"
          >
            {isRunning
              ? <Loader2 className="size-4 animate-spin" />
              : activeTab === "compare"
              ? <GitCompare className="size-4" />
              : <SearchX className="size-4" />}
            {isRunning
              ? "Analysing…"
              : activeTab === "compare"
              ? "Compare papers"
              : "Find research gaps"}
          </Button>
          <p className="text-xs text-muted-foreground">
            {selected.length < 2
              ? `Select ${2 - selected.length} more paper${2 - selected.length === 1 ? "" : "s"} to begin`
              : `${selected.length} papers selected · max 10`}
          </p>
        </div>

        {/* ── Results ── */}
        {currentId && (
          <>
            <Separator />
            {currentLoading || isRunning ? (
              <LoadingSkeleton
                label={
                  activeTab === "compare"
                    ? "Comparing papers… this takes 15–30 seconds."
                    : "Finding research gaps… this takes 15–30 seconds."
                }
              />
            ) : isDone && currentResult?.data ? (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                {activeTab === "compare" ? (
                  <CompareResults
                    data={currentResult.data as ComparisonData}
                    onRefresh={() => run(true)}
                    isRefreshing={compare.isPending}
                  />
                ) : (
                  <GapResults
                    data={currentResult.data as GapFinderData}
                    onRefresh={() => run(true)}
                    isRefreshing={findGaps.isPending}
                  />
                )}
              </motion.div>
            ) : null}
          </>
        )}
      </div>
    </PageContainer>
  );
}
