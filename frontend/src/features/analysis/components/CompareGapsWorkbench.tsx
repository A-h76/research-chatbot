import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  GitCompare,
  Loader2,
  RefreshCw,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Lightbulb,
  ArrowRight,
  FileText,
  Zap,
  SearchX,
  BookOpen,
  FlaskConical,
  HelpCircle,
  Database,
  GraduationCap,
  Copy,
  Search,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { useCompare, useComparison, useFindGaps, useGapResult } from "../useAnalysis";
import { useClipboard } from "@/hooks/useClipboard";
import { toast } from "@/components/common/Toast";
import { cn } from "@/lib/utils";
import type { ComparisonData, GapFinderData, UserFile } from "@/types/api";
import { ConsensusConflictStrip } from "@/features/evidence/components/ConsensusConflictStrip";
import { useProjectConsensusConflict } from "@/features/evidence/hooks/useProjectConsensusConflict";

function PaperRow({
  file,
  selected,
  onToggle,
}: {
  file: UserFile;
  selected: boolean;
  onToggle: () => void;
}) {
  const title = file.title || file.name;
  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        "flex w-full items-center gap-3 border-b border-border px-2 py-2 text-left last:border-0 transition-colors",
        selected ? "bg-accent-soft/50" : "hover:bg-muted/40",
      )}
    >
      <span
        className={cn(
          "flex size-5 shrink-0 items-center justify-center rounded border",
          selected
            ? "border-primary bg-primary text-primary-foreground"
            : "border-border bg-card",
        )}
      >
        {selected ? <CheckCircle2 className="size-3.5" /> : null}
      </span>
      <FileText className="size-3.5 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium">{title}</p>
        <p className="truncate text-[11px] text-muted-foreground">
          {[file.authors?.split(";")[0]?.trim(), file.year].filter(Boolean).join(" · ") ||
            "No metadata"}
        </p>
      </div>
    </button>
  );
}

function ResultSection({
  icon,
  title,
  children,
  defaultOpen = true,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/40"
      >
        <span className="text-muted-foreground">{icon}</span>
        <span className="flex-1 text-[13px] font-semibold">{title}</span>
        {open ? (
          <ChevronUp className="size-3.5 text-muted-foreground" />
        ) : (
          <ChevronDown className="size-3.5 text-muted-foreground" />
        )}
      </button>
      {open && <div className="border-t border-border px-3 py-2.5">{children}</div>}
    </div>
  );
}

function BulletList({ items }: { items?: string[] }) {
  if (!items?.length) {
    return <p className="text-[13px] italic text-muted-foreground">None identified.</p>;
  }
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-[13px] text-foreground/90">
          <span className="mt-1.5 size-1 shrink-0 rounded-full bg-muted-foreground/50" />
          <span className="leading-relaxed">{item}</span>
        </li>
      ))}
    </ul>
  );
}

function resultsToText(
  tab: "compare" | "gaps",
  data: ComparisonData | GapFinderData,
): string {
  const lines: string[] = [];
  if (tab === "compare") {
    const d = data as ComparisonData;
    if (d.overview) lines.push(`Overview\n${d.overview}`);
    if (d.similarities?.length) lines.push(`Similarities\n- ${d.similarities.join("\n- ")}`);
    if (d.differences?.length) lines.push(`Differences\n- ${d.differences.join("\n- ")}`);
    if (d.contradictions?.length) {
      lines.push(`Contradictions\n- ${d.contradictions.join("\n- ")}`);
    }
    if (d.synthesis) lines.push(`Synthesis\n${d.synthesis}`);
  } else {
    const d = data as GapFinderData;
    if (d.preamble) lines.push(`Overview\n${d.preamble}`);
    if (d.underexplored_topics?.length) {
      lines.push(`Underexplored\n- ${d.underexplored_topics.join("\n- ")}`);
    }
    if (d.open_questions?.length) {
      lines.push(`Open questions\n- ${d.open_questions.join("\n- ")}`);
    }
    if (d.potential_thesis_ideas?.length) {
      lines.push(`Thesis ideas\n- ${d.potential_thesis_ideas.join("\n- ")}`);
    }
  }
  return lines.join("\n\n");
}

function CompareResults({
  data,
  onRefresh,
  isRefreshing,
  onCopy,
}: {
  data: ComparisonData;
  onRefresh: () => void;
  isRefreshing: boolean;
  onCopy: () => void;
}) {
  if (data.error) {
    return (
      <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4">
        <p className="font-medium text-destructive">Analysis failed</p>
        <p className="mt-1 text-[13px] text-muted-foreground">{data.error}</p>
        <Button size="sm" variant="outline" className="mt-3 gap-2" onClick={onRefresh} disabled={isRefreshing}>
          <RefreshCw className={cn("size-3.5", isRefreshing && "animate-spin")} /> Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end gap-1">
        <Button size="sm" variant="outline" className="h-7 gap-1 text-[12px]" onClick={onCopy}>
          <Copy className="size-3" /> Copy
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="h-7 gap-1 text-[12px] text-muted-foreground"
          onClick={onRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={cn("size-3", isRefreshing && "animate-spin")} /> Re-run
        </Button>
      </div>
      {data.overview && (
        <div className="rounded-lg border border-border bg-card px-3 py-2.5">
          <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Overview
          </p>
          <p className="text-[13px] leading-relaxed">{data.overview}</p>
        </div>
      )}
      {data.methodologies && Object.keys(data.methodologies).length > 0 && (
        <ResultSection icon={<FileText className="size-3.5" />} title="Methodology by paper">
          <dl className="space-y-2">
            {Object.entries(data.methodologies).map(([t, m]) => (
              <div key={t}>
                <dt className="text-[12px] font-semibold">{t}</dt>
                <dd className="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">{m}</dd>
              </div>
            ))}
          </dl>
        </ResultSection>
      )}
      <div className="grid gap-2 sm:grid-cols-2">
        <ResultSection icon={<CheckCircle2 className="size-3.5" />} title="Similarities">
          <BulletList items={data.similarities} />
        </ResultSection>
        <ResultSection icon={<GitCompare className="size-3.5" />} title="Differences">
          <BulletList items={data.differences} />
        </ResultSection>
        <ResultSection icon={<CheckCircle2 className="size-3.5" />} title="Agreements">
          <BulletList items={data.agreements} />
        </ResultSection>
        <ResultSection
          icon={<AlertTriangle className="size-3.5" />}
          title="Contradictions"
          defaultOpen={false}
        >
          <BulletList items={data.contradictions} />
        </ResultSection>
      </div>
      {(data.common_datasets?.length ?? 0) > 0 && (
        <ResultSection icon={<Zap className="size-3.5" />} title="Common datasets">
          <div className="flex flex-wrap gap-1.5">
            {data.common_datasets!.map((ds) => (
              <Badge key={ds} variant="outline" className="text-[11px] font-normal">
                {ds}
              </Badge>
            ))}
          </div>
        </ResultSection>
      )}
      {(data.research_trends?.length ?? 0) > 0 && (
        <ResultSection icon={<ArrowRight className="size-3.5" />} title="Research trends">
          <BulletList items={data.research_trends} />
        </ResultSection>
      )}
      {data.synthesis && (
        <ResultSection icon={<Lightbulb className="size-3.5" />} title="Synthesis">
          <p className="text-[13px] leading-relaxed">{data.synthesis}</p>
        </ResultSection>
      )}
    </div>
  );
}

function GapResults({
  data,
  onRefresh,
  isRefreshing,
  onCopy,
}: {
  data: GapFinderData;
  onRefresh: () => void;
  isRefreshing: boolean;
  onCopy: () => void;
}) {
  if (data.error) {
    return (
      <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4">
        <p className="font-medium text-destructive">Analysis failed</p>
        <p className="mt-1 text-[13px] text-muted-foreground">{data.error}</p>
        <Button size="sm" variant="outline" className="mt-3 gap-2" onClick={onRefresh} disabled={isRefreshing}>
          <RefreshCw className={cn("size-3.5", isRefreshing && "animate-spin")} /> Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end gap-1">
        <Button size="sm" variant="outline" className="h-7 gap-1 text-[12px]" onClick={onCopy}>
          <Copy className="size-3" /> Copy
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="h-7 gap-1 text-[12px] text-muted-foreground"
          onClick={onRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={cn("size-3", isRefreshing && "animate-spin")} /> Re-run
        </Button>
      </div>
      <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 dark:border-amber-800 dark:bg-amber-950/40">
        <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-600" />
        <p className="text-[12px] leading-relaxed text-amber-800 dark:text-amber-300">
          {data.disclaimer ??
            "AI-generated suggestions — starting points for your own critical assessment."}
        </p>
      </div>
      {data.preamble && (
        <div className="rounded-lg border border-border bg-card px-3 py-2.5">
          <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Field overview
          </p>
          <p className="text-[13px] leading-relaxed">{data.preamble}</p>
        </div>
      )}
      <div className="grid gap-2 sm:grid-cols-2">
        <ResultSection icon={<SearchX className="size-3.5" />} title="Underexplored topics">
          <BulletList items={data.underexplored_topics} />
        </ResultSection>
        <ResultSection icon={<FlaskConical className="size-3.5" />} title="Missing experiments">
          <BulletList items={data.missing_experiments} />
        </ResultSection>
        <ResultSection icon={<HelpCircle className="size-3.5" />} title="Open questions">
          <BulletList items={data.open_questions} />
        </ResultSection>
        <ResultSection
          icon={<AlertTriangle className="size-3.5" />}
          title="Methodological gaps"
          defaultOpen={false}
        >
          <BulletList items={data.methodological_gaps} />
        </ResultSection>
        <ResultSection icon={<Database className="size-3.5" />} title="Dataset gaps" defaultOpen={false}>
          <BulletList items={data.dataset_gaps} />
        </ResultSection>
        <ResultSection icon={<GraduationCap className="size-3.5" />} title="Thesis ideas">
          <BulletList items={data.potential_thesis_ideas} />
        </ResultSection>
      </div>
      {(data.future_opportunities?.length ?? 0) > 0 && (
        <ResultSection icon={<BookOpen className="size-3.5" />} title="Future opportunities">
          <BulletList items={data.future_opportunities} />
        </ResultSection>
      )}
    </div>
  );
}

type ActiveTab = "compare" | "gaps";

/** Shared compare/gaps workbench — used on /research/compare and in project workspace. */
export function CompareGapsWorkbench({
  files,
  projectId,
  emptyTitle = "No analysed papers yet",
  emptyDescription = "Upload papers and wait for analysis before comparing.",
}: {
  files: UserFile[];
  projectId: number | null;
  emptyTitle?: string;
  emptyDescription?: string;
}) {
  const { copy } = useClipboard();
  const [activeTab, setActiveTab] = useState<ActiveTab>("compare");
  const [selected, setSelected] = useState<number[]>([]);
  const [searchQ, setSearchQ] = useState("");

  const [compId, setCompId] = useState<number | null>(null);
  const compare = useCompare();
  const { data: compResult, isLoading: compLoading } = useComparison(compId);

  const [gapsId, setGapsId] = useState<number | null>(null);
  const findGaps = useFindGaps();
  const { data: gapsResult, isLoading: gapsLoading } = useGapResult(gapsId);

  const riCompare = useProjectConsensusConflict({
    projectId,
    fileIds: selected,
    enabled: activeTab === "compare" && selected.length >= 2 && projectId != null,
  });

  const filtered = useMemo(() => {
    const q = searchQ.trim().toLowerCase();
    if (!q) return files;
    return files.filter((f) => {
      const hay = [f.title, f.name, f.authors, f.year].join(" ").toLowerCase();
      return hay.includes(q);
    });
  }, [files, searchQ]);

  function toggleFile(id: number) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  async function run(force = false) {
    if (selected.length < 2) {
      toast.error("Select at least 2 papers.");
      return;
    }
    const input = { file_ids: selected, project_id: projectId, force };
    try {
      if (activeTab === "compare") {
        const r = await compare.mutateAsync(input);
        if (r.skipped?.length) {
          toast.warning(
            `Skipped: ${r.skipped.map((s) => s.name ?? `#${s.id}`).join(", ")}`,
          );
        }
        setCompId(r.id);
      } else {
        const r = await findGaps.mutateAsync(input);
        if (r.skipped?.length) {
          toast.warning(
            `Skipped: ${r.skipped.map((s) => s.name ?? `#${s.id}`).join(", ")}`,
          );
        }
        setGapsId(r.id);
      }
    } catch {
      toast.error("Could not start analysis.");
    }
  }

  const isPending = activeTab === "compare" ? compare.isPending : findGaps.isPending;
  const isRunning =
    isPending ||
    (activeTab === "compare"
      ? compResult?.status === "running"
      : gapsResult?.status === "running");

  const currentId = activeTab === "compare" ? compId : gapsId;
  const currentResult = activeTab === "compare" ? compResult : gapsResult;
  const currentLoading = activeTab === "compare" ? compLoading : gapsLoading;
  const isDone = currentResult?.status === "done";

  function handleCopy() {
    if (!currentResult?.data) return;
    copy(resultsToText(activeTab, currentResult.data as ComparisonData | GapFinderData));
    toast.success("Results copied");
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 border-b border-border pb-3">
        <div className="flex items-center gap-0.5 rounded-md border border-border p-0.5">
          {(
            [
              { key: "compare" as const, label: "Compare", icon: GitCompare },
              { key: "gaps" as const, label: "Gaps", icon: SearchX },
            ] as const
          ).map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              onClick={() => setActiveTab(key)}
              className={cn(
                "inline-flex h-8 items-center gap-1.5 rounded px-2.5 text-[12px] font-medium",
                activeTab === key
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="size-3.5" /> {label}
            </button>
          ))}
        </div>

        <div className="flex min-w-[10rem] flex-1 items-center gap-2 rounded-md border border-border bg-card px-2.5 py-1.5">
          <Search className="size-3.5 shrink-0 text-muted-foreground" />
          <input
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            placeholder="Filter analysed papers…"
            className="w-full bg-transparent text-[13px] outline-none placeholder:text-muted-foreground"
          />
          {searchQ && (
            <button type="button" onClick={() => setSearchQ("")} aria-label="Clear">
              <X className="size-3.5 text-muted-foreground" />
            </button>
          )}
        </div>

        {selected.length > 0 && (
          <button
            type="button"
            onClick={() => setSelected([])}
            className="text-[12px] text-muted-foreground hover:text-foreground"
          >
            Clear ({selected.length})
          </button>
        )}

        <Button
          size="sm"
          className="h-8 gap-1.5 text-[12px]"
          onClick={() => run(false)}
          disabled={selected.length < 2 || isRunning}
        >
          {isRunning ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : activeTab === "compare" ? (
            <GitCompare className="size-3.5" />
          ) : (
            <SearchX className="size-3.5" />
          )}
          {isRunning
            ? "Running…"
            : activeTab === "compare"
              ? "Run compare"
              : "Find gaps"}
        </Button>
      </div>

      <p className="text-[12px] text-muted-foreground">
        {activeTab === "compare"
          ? "Similarities, differences, contradictions, synthesis — 2–10 analysed papers."
          : "Underexplored topics, open questions, thesis ideas — 2–10 analysed papers."}
      </p>

      {activeTab === "compare" && selected.length >= 2 ? (
        <ConsensusConflictStrip
          status={riCompare.status}
          consensus={riCompare.consensus}
          conflict={riCompare.conflict}
        />
      ) : null}

      {files.length === 0 ? (
        <EmptyState
          icon={<FileText className="size-7" />}
          title={emptyTitle}
          description={emptyDescription}
        />
      ) : filtered.length === 0 ? (
        <p className="text-[13px] text-muted-foreground">No papers match your filter.</p>
      ) : (
        <div className="max-h-[14rem] overflow-y-auto rounded-lg border border-border bg-card">
          {filtered.map((f) => (
            <PaperRow
              key={f.id}
              file={f}
              selected={selected.includes(f.id)}
              onToggle={() => toggleFile(f.id)}
            />
          ))}
        </div>
      )}

      {currentId && (
        <div className="border-t border-border pt-3">
          {currentLoading || isRunning ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                {activeTab === "compare"
                  ? "Comparing… usually 15–30s."
                  : "Finding gaps… usually 15–30s."}
              </div>
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-16 rounded-lg" />
              ))}
            </div>
          ) : isDone && currentResult?.data ? (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              {activeTab === "compare" ? (
                <CompareResults
                  data={currentResult.data as ComparisonData}
                  onRefresh={() => run(true)}
                  isRefreshing={compare.isPending}
                  onCopy={handleCopy}
                />
              ) : (
                <GapResults
                  data={currentResult.data as GapFinderData}
                  onRefresh={() => run(true)}
                  isRefreshing={findGaps.isPending}
                  onCopy={handleCopy}
                />
              )}
            </motion.div>
          ) : null}
        </div>
      )}
    </div>
  );
}
