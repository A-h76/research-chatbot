import { ArrowRight } from "lucide-react";
import {
  RI_CATEGORIES,
  type RiCategoryId,
  type RiTab,
} from "../researchIntelligenceNav";
import { cn } from "@/lib/utils";

/**
 * Workflow category landing — dashboard for a stage, not a tool launcher wall.
 * Answers: what this stage is for, readiness, and which lens to open next.
 */
export function ResearchIntelligenceCategoryLanding({
  categoryId,
  onOpenTab,
  metrics,
}: {
  categoryId: RiCategoryId;
  onOpenTab: (tab: RiTab) => void;
  metrics: {
    papers: number;
    evidence: number;
    themes: number;
    gaps: number;
    methods: number;
    coverage: number | null;
    contradictions: number;
    unknownCells: number;
  };
}) {
  const cat = RI_CATEGORIES.find((c) => c.id === categoryId);
  if (!cat) return null;

  const readiness = (() => {
    if (metrics.papers === 0) {
      return {
        status: "Empty corpus",
        detail: "Add papers before this stage can do useful work.",
        next: { label: "Go to Library", href: "/library" as const, tab: null },
      };
    }
    if (metrics.evidence === 0) {
      return {
        status: "Awaiting extraction",
        detail: "Extract evidence so this stage has grounded material to work with.",
        next: {
          label: "Open Structured Evidence",
          href: null,
          tab: "extract" as RiTab,
        },
      };
    }
    if (categoryId === "understand" && metrics.unknownCells > 0) {
      return {
        status: "Partial coverage",
        detail: `${metrics.unknownCells} matrix cells still need extraction.`,
        next: {
          label: "Continue extraction",
          href: null,
          tab: "extract" as RiTab,
        },
      };
    }
    if (categoryId === "insights" && metrics.gaps > 0) {
      return {
        status: "Gaps ready to review",
        detail: `${metrics.gaps} research gap${metrics.gaps === 1 ? "" : "s"} detected from coverage.`,
        next: { label: "Review research gaps", href: null, tab: "gaps" as RiTab },
      };
    }
    if (categoryId === "relationships" && metrics.evidence > 0) {
      return {
        status: "Ready to explore",
        detail: "Graph and timeline can map connections across extracted evidence.",
        next: { label: "Open Graph", href: null, tab: "graph" as RiTab },
      };
    }
    if (categoryId === "synthesis") {
      return {
        status: metrics.evidence > 0 ? "Ready to compare" : "Needs evidence",
        detail:
          metrics.evidence > 0
            ? "Compare papers side by side, then carry insights into Writing."
            : "Extract evidence before synthesis is meaningful.",
        next: {
          label: metrics.evidence > 0 ? "Compare Papers" : "Open Structured Evidence",
          href: null,
          tab: (metrics.evidence > 0 ? "compare" : "extract") as RiTab,
        },
      };
    }
    return {
      status: "Ready",
      detail: "Open a lens below — or return to Overview for the next recommended action.",
      next: {
        label: cat.children[0] ? `Open ${cat.children[0].label}` : "Back to Overview",
        href: null,
        tab: (cat.children[0]?.key ?? "overview") as RiTab,
      },
    };
  })();

  const signals: { label: string; value: string }[] = [
    { label: "Papers", value: String(metrics.papers) },
    { label: "Evidence", value: String(metrics.evidence) },
  ];
  if (categoryId === "understand") {
    signals.push(
      { label: "Themes", value: String(metrics.themes) },
      {
        label: "Coverage",
        value:
          metrics.coverage == null ? "—" : `${Math.round(metrics.coverage * 100)}%`,
      },
    );
  }
  if (categoryId === "relationships") {
    signals.push({
      label: "Contradictions",
      value: String(metrics.contradictions),
    });
  }
  if (categoryId === "insights") {
    signals.push(
      { label: "Gaps", value: String(metrics.gaps) },
      { label: "Method cards", value: String(metrics.methods) },
    );
  }
  if (categoryId === "synthesis") {
    signals.push(
      { label: "Themes", value: String(metrics.themes) },
      { label: "Gaps", value: String(metrics.gaps) },
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
          {cat.label}
        </p>
        <h2 className="text-[18px] font-semibold tracking-tight text-foreground">
          {cat.question}
        </h2>
        <p className="max-w-xl text-[13px] leading-relaxed text-muted-foreground">
          {cat.job}
        </p>
      </header>

      <section
        aria-label={`${cat.label} readiness`}
        className="rounded-lg border border-border bg-card px-4 py-3"
      >
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Readiness
        </p>
        <p className="mt-1 text-[14px] font-semibold text-foreground">{readiness.status}</p>
        <p className="mt-0.5 text-[13px] text-muted-foreground">{readiness.detail}</p>
        {readiness.next.href ? (
          <a
            href={readiness.next.href}
            className="mt-2 inline-flex items-center gap-1.5 text-[13px] font-medium text-primary hover:underline"
          >
            {readiness.next.label}
            <ArrowRight className="size-3.5" />
          </a>
        ) : (
          <button
            type="button"
            onClick={() => readiness.next.tab && onOpenTab(readiness.next.tab)}
            className="mt-2 inline-flex items-center gap-1.5 text-[13px] font-medium text-primary hover:underline"
          >
            {readiness.next.label}
            <ArrowRight className="size-3.5" />
          </button>
        )}
      </section>

      <section aria-label={`${cat.label} signals`}>
        <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Signals
        </p>
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-[13px]">
          {signals.map((s) => (
            <span key={s.label} className="inline-flex items-baseline gap-1.5">
              <span className="tabular-nums font-semibold text-foreground">{s.value}</span>
              <span className="text-muted-foreground">{s.label}</span>
            </span>
          ))}
        </div>
      </section>

      {cat.children.length > 0 ? (
        <section aria-label={`${cat.label} lenses`}>
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Lenses in this stage
          </p>
          <ul className="grid gap-2 sm:grid-cols-2">
            {cat.children.map((child) => {
              const Icon = child.icon;
              return (
                <li key={child.key}>
                  <button
                    type="button"
                    onClick={() => onOpenTab(child.key)}
                    className={cn(
                      "flex w-full items-start gap-2.5 rounded-lg border border-border bg-card px-3 py-2.5 text-left transition-colors hover:bg-muted/40",
                    )}
                  >
                    <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0">
                      <span className="block text-[13px] font-semibold text-foreground">
                        {child.label}
                      </span>
                      <span className="mt-0.5 block text-[12px] text-muted-foreground">
                        {child.question}
                      </span>
                    </span>
                    <ArrowRight className="ml-auto mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      ) : (
        <p className="text-[13px] text-muted-foreground">
          Synthesis will grow here (literature review, discussion, research questions). Compare
          Papers appears when enabled in research preferences.
        </p>
      )}
    </div>
  );
}
