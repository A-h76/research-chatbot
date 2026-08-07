import { Link } from "react-router-dom";
import { ArrowRight, LayoutDashboard, Loader2 } from "lucide-react";
import { EmptyState } from "@/components/common/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { useRiCorpusMetrics } from "../hooks/useRiCorpusMetrics";
import type { RiTab } from "../researchIntelligenceNav";
import { cn } from "@/lib/utils";

type Recommendation = {
  title: string;
  reason: string;
  impact: string;
  estimate: string;
  actionLabel: string;
  tab?: RiTab;
  href?: string;
};

/**
 * Mission Control — corpus state + next action.
 * Not a tool launcher. Answers: what is happening, what should I do next?
 */
export function ResearchIntelligenceOverview({
  projectId,
  onOpenTab,
}: {
  projectId: number | null;
  onOpenTab: (tab: RiTab) => void;
  /** @deprecated Open shortcuts removed — kept for call-site compat. */
  showCompare?: boolean;
}) {
  const m = useRiCorpusMetrics(projectId);

  if (projectId == null) {
    return (
      <EmptyState
        icon={<LayoutDashboard className="size-7" />}
        title="Select a project"
        description="Open a project to see Research Intelligence for its corpus."
      />
    );
  }

  if (m.loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-[13px] text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Loading corpus intelligence…
        </div>
        <Skeleton className="h-28 w-full rounded-lg" />
        <Skeleton className="h-24 w-full rounded-lg" />
      </div>
    );
  }

  const progress = (() => {
    if (m.papers === 0) return 0;
    let score = 0;
    if (m.papers > 0) score += 20;
    if (m.evidence > 0) score += 30;
    if (m.themes > 0) score += 15;
    if ((m.coverage ?? 0) >= 0.5) score += 15;
    else if ((m.coverage ?? 0) > 0) score += 8;
    if (m.gaps >= 0 && m.evidence > 0) score += 10;
    if (m.methods > 0) score += 10;
    return Math.min(100, score);
  })();

  const maturity: "empty" | "imported" | "extracted" | "mature" = (() => {
    if (m.papers === 0) return "empty";
    if (m.evidence === 0) return "imported";
    if (m.themes > 0 && (m.gaps > 0 || m.contradictions > 0 || (m.coverage ?? 0) > 0.4)) {
      return "mature";
    }
    return "extracted";
  })();

  const remainingPapers = Math.max(0, m.papers - m.papersWithEvidence);

  const recommendation: Recommendation = (() => {
    if (maturity === "empty") {
      return {
        title: "Upload papers",
        reason: "Research Intelligence needs a corpus before it can understand, relate, or synthesise.",
        impact: "Unlocks extraction, themes, gaps, and comparison.",
        estimate: "A few minutes",
        actionLabel: "Open Library",
        href: "/library",
      };
    }
    if (maturity === "imported") {
      return {
        title: "Extract evidence",
        reason:
          "Without extraction Dhund cannot discover themes, contradictions, or relationships.",
        impact: "Fills Matrix, Themes, Graph, Gaps, and Synthesis.",
        estimate: remainingPapers > 0 ? `~${Math.max(2, remainingPapers)}–${remainingPapers * 2} min` : "3–5 minutes",
        actionLabel: "Start extraction",
        tab: "extract",
      };
    }
    if (m.unknownCells > 8 || remainingPapers > 0) {
      return {
        title: "Finish extraction coverage",
        reason:
          remainingPapers > 0
            ? `${remainingPapers} paper${remainingPapers === 1 ? "" : "s"} still lack extracted evidence.`
            : `${m.unknownCells} matrix cells are still not extracted.`,
        impact: "Improves theme quality, gap detection, and compare accuracy.",
        estimate: "2–4 minutes",
        actionLabel: "Continue in Structured Evidence",
        tab: "extract",
      };
    }
    if (m.gaps > 0) {
      return {
        title: "Review research gaps",
        reason: `${m.gaps} coverage gap${m.gaps === 1 ? "" : "s"} detected from themes and matrix density.`,
        impact: "Clarifies where your literature review or proposal should go next.",
        estimate: "5–10 minutes",
        actionLabel: "Open Gap Review",
        tab: "gaps",
      };
    }
    if (m.hasConflict || m.contradictions > 0) {
      return {
        title: "Inspect contradictions",
        reason: m.conflictSummary || "Conflicting evidence pairs appear in this corpus.",
        impact: "Prevents overconfident synthesis and surfaces mediators.",
        estimate: "5 minutes",
        actionLabel: "Explore Graph",
        tab: "graph",
      };
    }
    if (maturity === "mature") {
      return {
        title: "Compare key papers",
        reason: "Your corpus is rich enough for side-by-side synthesis.",
        impact: "Produces differences, agreements, and writing-ready insights.",
        estimate: "5–8 minutes",
        actionLabel: "Open Compare Papers",
        tab: "compare",
      };
    }
    return {
      title: "Explore Evidence Matrix",
      reason: "See method, dataset, findings, and limitations across papers.",
      impact: "Builds a shared mental model of the corpus.",
      estimate: "3–5 minutes",
      actionLabel: "Open Evidence Matrix",
      tab: "matrix",
    };
  })();

  const discoveries: string[] = [];
  for (const label of m.themeLabels) discoveries.push(`Theme detected · ${label}`);
  if (m.methods > 0) discoveries.push(`Method cluster ready · ${m.methods} advisory card${m.methods === 1 ? "" : "s"}`);
  if (m.hasConflict || m.contradictions > 0) {
    discoveries.push(
      m.conflictSummary
        ? `Contradiction · ${m.conflictSummary}`
        : `${m.contradictions} contradiction link${m.contradictions === 1 ? "" : "s"}`,
    );
  }
  for (const g of m.gapStatements) discoveries.push(`Gap · ${g}`);

  const activity: string[] = [];
  if (m.evidence > 0) activity.push(`${m.evidence} evidence object${m.evidence === 1 ? "" : "s"} in corpus`);
  if (m.themes > 0) activity.push(`${m.themes} theme cluster${m.themes === 1 ? "" : "s"} available`);
  if (m.gaps > 0) activity.push(`${m.gaps} research gap${m.gaps === 1 ? "" : "s"} flagged`);
  if (m.coverage != null) activity.push(`Matrix coverage ${Math.round(m.coverage * 100)}%`);
  if (activity.length === 0) {
    activity.push(
      maturity === "empty"
        ? "No research activity yet — start by uploading papers."
        : "Waiting on first evidence extraction.",
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
          Research Intelligence
        </p>
        <h2 className="text-[18px] font-semibold tracking-tight text-foreground">
          Mission Control
        </h2>
        <p className="max-w-xl text-[13px] leading-relaxed text-muted-foreground">
          Corpus health, discoveries, and the next best research action — not a menu of tools.
        </p>
      </header>

      {/* Corpus health */}
      <section
        aria-label="Corpus health"
        className="rounded-lg border border-border bg-card px-4 py-3.5"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Corpus health
          </p>
          <p className="text-[12px] tabular-nums text-muted-foreground">
            Research readiness · {progress}%
          </p>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary/70 transition-[width]"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-[13px]">
          {(
            [
              ["Papers", m.papers],
              ["Evidence", m.evidence],
              ["Themes", m.themes],
              ["Gaps", m.gaps],
              ["Contradictions", m.contradictions],
            ] as const
          ).map(([label, value]) => (
            <span key={label} className="inline-flex items-baseline gap-1.5">
              <span className="tabular-nums font-semibold text-foreground">{value}</span>
              <span className="text-muted-foreground">{label}</span>
            </span>
          ))}
          {m.coverage != null ? (
            <span className="inline-flex items-baseline gap-1.5">
              <span className="tabular-nums font-semibold text-foreground">
                {Math.round(m.coverage * 100)}%
              </span>
              <span className="text-muted-foreground">Coverage</span>
            </span>
          ) : null}
        </div>
      </section>

      {/* Recommended next */}
      <section
        aria-label="Recommended next action"
        className="rounded-lg border border-primary/25 bg-primary/[0.04] px-4 py-3.5"
      >
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Recommended next step
        </p>
        <h3 className="mt-1 text-[15px] font-semibold tracking-tight text-foreground">
          {recommendation.title}
        </h3>
        <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
          {recommendation.reason}
        </p>
        <dl className="mt-3 grid gap-2 text-[12px] sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">Impact</dt>
            <dd className="text-foreground/90">{recommendation.impact}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Estimated time</dt>
            <dd className="text-foreground/90">{recommendation.estimate}</dd>
          </div>
        </dl>
        <div className="mt-3">
          {recommendation.href ? (
            <Link
              to={recommendation.href}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-2.5 text-[12px] font-medium text-primary-foreground hover:bg-primary/80"
            >
              {recommendation.actionLabel}
              <ArrowRight className="size-3.5" />
            </Link>
          ) : (
            <button
              type="button"
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-2.5 text-[12px] font-medium text-primary-foreground hover:bg-primary/80"
              onClick={() => recommendation.tab && onOpenTab(recommendation.tab)}
            >
              {recommendation.actionLabel}
              <ArrowRight className="size-3.5" />
            </button>
          )}
        </div>
      </section>

      {/* Discoveries — only when something exists */}
      {discoveries.length > 0 ? (
        <section aria-label="Recent discoveries">
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Latest discoveries
          </p>
          <ul className="space-y-1.5">
            {discoveries.slice(0, 6).map((d) => (
              <li
                key={d}
                className={cn(
                  "rounded-md border border-border/80 bg-card px-3 py-2 text-[13px] text-foreground/90",
                )}
              >
                {d}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-label="Recent activity">
        <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Research state
        </p>
        <ul className="space-y-1 text-[13px] text-muted-foreground">
          {activity.map((a) => (
            <li key={a} className="flex gap-2">
              <span className="text-foreground/40" aria-hidden>
                ·
              </span>
              <span>{a}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[12px] text-muted-foreground">
          Workflow: Understand → Relationships → Insights → Synthesis
        </p>
      </section>
    </div>
  );
}
