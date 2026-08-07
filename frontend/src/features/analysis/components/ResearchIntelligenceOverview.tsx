import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ClipboardList,
  GitCompare,
  LayoutDashboard,
  Loader2,
  Network,
  SearchX,
  Table2,
} from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { evidenceApi } from "@/features/evidence/api";
import { useProjectConsensusConflict } from "@/features/evidence/hooks/useProjectConsensusConflict";
import { cn } from "@/lib/utils";

type LensTab =
  | "matrix"
  | "extract"
  | "themes"
  | "gaps"
  | "graph"
  | "timeline"
  | "methodology"
  | "compare";

/**
 * Research Intelligence Overview — corpus health + suggested next action.
 * GitHub Insights–style landing before diving into lenses.
 */
export function ResearchIntelligenceOverview({
  projectId,
  onOpenTab,
  showCompare,
}: {
  projectId: number | null;
  onOpenTab: (tab: LensTab) => void;
  showCompare?: boolean;
}) {
  const enabled = projectId != null;
  const matrixQ = useQuery({
    queryKey: ["evidence", "matrix", projectId, ""],
    queryFn: () => evidenceApi.matrix(projectId as number),
    enabled,
    staleTime: 30_000,
  });
  const themesQ = useQuery({
    queryKey: ["evidence", "themes", projectId, ""],
    queryFn: () => evidenceApi.themes(projectId as number),
    enabled,
    staleTime: 30_000,
  });
  const gapsQ = useQuery({
    queryKey: ["evidence", "gaps", projectId],
    queryFn: () => evidenceApi.gaps(projectId as number),
    enabled,
    staleTime: 30_000,
  });
  const methodologyQ = useQuery({
    queryKey: ["evidence", "methodology", projectId, ""],
    queryFn: () => evidenceApi.methodology(projectId as number),
    enabled,
    staleTime: 30_000,
  });
  const ri = useProjectConsensusConflict({ projectId, enabled });

  if (!enabled) {
    return (
      <EmptyState
        icon={<LayoutDashboard className="size-7" />}
        title="Select a project"
        description="Open a project to see Research Intelligence for its corpus."
      />
    );
  }

  const loading =
    matrixQ.isLoading || themesQ.isLoading || gapsQ.isLoading || methodologyQ.isLoading;

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Loading corpus intelligence…
        </div>
        <Skeleton className="h-24 w-full rounded-lg" />
        <Skeleton className="h-16 w-full rounded-lg" />
      </div>
    );
  }

  const papers = matrixQ.data?.metrics.paper_count ?? 0;
  const evidence =
    gapsQ.data?.metrics.evidence_count ?? matrixQ.data?.metrics.papers_with_evidence ?? 0;
  const themes = themesQ.data?.metrics.theme_count ?? 0;
  const methods = methodologyQ.data?.metrics.card_count ?? 0;
  const gaps = gapsQ.data?.metrics.gap_count ?? 0;
  const unknownCells = matrixQ.data?.metrics.cell_unknown ?? 0;
  const conflictCount = ri.conflict?.has_conflict ? 1 : 0;

  const nextAction: {
    label: string;
    hint: string;
    tab?: LensTab;
    href?: string;
  } = (() => {
    if (papers === 0) {
      return {
        label: "Add papers to this project",
        hint: "Research Intelligence needs a corpus to analyse.",
        href: "/library",
      };
    }
    if (evidence === 0 || unknownCells > 0) {
      return {
        label: "Open Structured Evidence",
        hint:
          evidence === 0
            ? "Extract evidence so themes, gaps, and the matrix can fill in."
            : `${unknownCells} matrix cells still need extraction.`,
        tab: "extract",
      };
    }
    if (gaps > 0) {
      return {
        label: "Review research gaps",
        hint: `${gaps} coverage gap${gaps === 1 ? "" : "s"} flagged.`,
        tab: "gaps",
      };
    }
    return {
      label: "Open Evidence Matrix",
      hint: "See what every paper says side by side.",
      tab: "matrix",
    };
  })();

  const stats: { label: string; value: number }[] = [
    { label: "Papers", value: papers },
    { label: "Evidence", value: evidence },
    { label: "Themes", value: themes },
    { label: "Method cards", value: methods },
    { label: "Gaps", value: gaps },
  ];
  if (conflictCount > 0) {
    stats.push({ label: "Contradictions", value: conflictCount });
  }

  const shortcuts: { label: string; tab: LensTab; icon: typeof Table2 }[] = [
    { label: "Evidence Matrix", tab: "matrix", icon: Table2 },
    { label: "Structured Evidence", tab: "extract", icon: ClipboardList },
    { label: "Graph", tab: "graph", icon: Network },
    { label: "Research Gaps", tab: "gaps", icon: SearchX },
  ];
  if (showCompare) {
    shortcuts.push({ label: "Compare Papers", tab: "compare", icon: GitCompare });
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
          Research Intelligence
        </p>
        <h2 className="text-[18px] font-semibold tracking-tight text-foreground">
          Understand this corpus
        </h2>
        <p className="max-w-xl text-[13px] leading-relaxed text-muted-foreground">
          Synthesis, themes, gaps, relationships, and comparison — grounded in extracted
          evidence from your project papers.
        </p>
      </header>

      <section aria-label="Corpus summary">
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-[13px]">
          {stats.map((s) => (
            <span key={s.label} className="inline-flex items-baseline gap-1.5">
              <span className="tabular-nums font-semibold text-foreground">{s.value}</span>
              <span className="text-muted-foreground">{s.label}</span>
            </span>
          ))}
        </div>
      </section>

      <section
        aria-label="Suggested next action"
        className="rounded-lg border border-border bg-card px-4 py-3"
      >
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Suggested next
        </p>
        <p className="mt-1 text-[13px] text-muted-foreground">{nextAction.hint}</p>
        {nextAction.href ? (
          <a
            href={nextAction.href}
            className="mt-2 inline-flex items-center gap-1.5 text-[13px] font-medium text-primary hover:text-primary/80"
          >
            {nextAction.label}
            <ArrowRight className="size-3.5" />
          </a>
        ) : (
          <button
            type="button"
            onClick={() => nextAction.tab && onOpenTab(nextAction.tab)}
            className="mt-2 inline-flex items-center gap-1.5 text-[13px] font-medium text-primary hover:text-primary/80"
          >
            {nextAction.label}
            <ArrowRight className="size-3.5" />
          </button>
        )}
      </section>

      <section aria-label="Open lenses">
        <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Open
        </p>
        <div className="flex flex-wrap gap-2">
          {shortcuts.map(({ label, tab, icon: Icon }) => (
            <button
              key={tab}
              type="button"
              onClick={() => onOpenTab(tab)}
              className={cn(
                "inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-background px-2.5 text-[12px] font-medium text-foreground transition-colors hover:bg-muted/60",
              )}
            >
              <Icon className="size-3.5 text-muted-foreground" />
              {label}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
