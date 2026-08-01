import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  FileText,
  Library,
  MessageSquare,
  PenLine,
  Plus,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { HomeResearchSkeleton } from "@/components/common/ResearchSkeletons";
import { AiStateBadge, usePipelines } from "@/features/pipeline";
import { useUI } from "@/context/UIContext";
import { useProjectHub } from "@/features/projects/useProjects";
import { evidenceApi } from "@/features/evidence/api";
import { writingApi } from "@/features/writing/api";
import { useDashboard } from "./useDashboard";
import { cn } from "@/lib/utils";
import type { DashboardPaperBrief } from "./api";
import type { WritingDocument } from "@/types/api";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
      {children}
    </p>
  );
}

function isWithinHours(iso: string | null | undefined, hours: number): boolean {
  if (!iso) return false;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return false;
  return Date.now() - t <= hours * 3600_000;
}

function formatRelative(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  const mins = Math.round((Date.now() - t) / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 48) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  return `${days}d ago`;
}

function ProgressBar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[11px] text-muted-foreground">{label}</span>
        <span className="text-[11px] tabular-nums text-muted-foreground">{pct}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function deriveStage(opts: {
  paper: DashboardPaperBrief | null;
  hasWriting: boolean;
  writingRecent: boolean;
  evidenceCount: number;
  themeCount: number;
}): string {
  if (opts.writingRecent) return "Writing";
  if (opts.hasWriting && opts.themeCount > 0) return "Literature synthesis";
  if (opts.evidenceCount > 0 || opts.themeCount > 0) return "Evidence review";
  if (opts.paper?.meta_status === "running") return "Analysing";
  if (opts.paper?.meta_status === "done" && opts.paper.reading_status === "reading") {
    return "Deep reading";
  }
  if (opts.paper?.reading_status === "reading") return "Reading";
  if (opts.paper?.meta_status === "done") return "Analysed — ready to synthesize";
  return "Getting started";
}

/** Launchpad = research command center. Hierarchy: continue → updates → work. */
export function DashboardPage() {
  const navigate = useNavigate();
  const { currentProjectId } = useUI();
  const { data, isLoading } = useDashboard();
  const { data: hub } = useProjectHub(currentProjectId);

  const { data: themes } = useQuery({
    queryKey: ["launchpad", "themes", currentProjectId],
    queryFn: () => evidenceApi.themes(currentProjectId as number),
    enabled: currentProjectId != null,
    staleTime: 60_000,
  });

  const { data: gaps } = useQuery({
    queryKey: ["launchpad", "gaps", currentProjectId],
    queryFn: () => evidenceApi.gaps(currentProjectId as number),
    enabled: currentProjectId != null,
    staleTime: 60_000,
  });

  const { data: evidenceList } = useQuery({
    queryKey: ["launchpad", "evidence", currentProjectId],
    queryFn: () => evidenceApi.list(currentProjectId as number),
    enabled: currentProjectId != null,
    staleTime: 60_000,
  });

  const { data: decisions } = useQuery({
    queryKey: ["launchpad", "decisions", currentProjectId],
    queryFn: () => evidenceApi.listDecisions(currentProjectId as number, 40),
    enabled: currentProjectId != null,
    staleTime: 60_000,
  });

  const { data: writingList } = useQuery({
    queryKey: ["launchpad", "writing", currentProjectId],
    queryFn: () => writingApi.listDocuments(currentProjectId as number),
    enabled: currentProjectId != null,
    staleTime: 60_000,
  });

  const focusPaper = useMemo(() => {
    if (!data) return null;
    return (
      data.current_papers[0] ??
      data.recent_papers.find((p) => p.meta_status === "done") ??
      data.recent_papers[0] ??
      null
    );
  }, [data]);

  const paperIds = useMemo(() => {
    if (!data) return [] as number[];
    const ids = new Set<number>();
    for (const p of [...data.current_papers, ...data.recent_papers]) ids.add(p.id);
    return [...ids];
  }, [data]);

  const metaById = useMemo(() => {
    const m: Record<number, string> = {};
    if (!data) return m;
    for (const p of [...data.current_papers, ...data.recent_papers]) {
      m[p.id] = p.meta_status;
    }
    return m;
  }, [data]);

  const { byId: pipelineById } = usePipelines(paperIds, metaById);

  const recentWriting = useMemo(() => {
    const items = writingList?.items ?? [];
    return [...items]
      .sort((a, b) => {
        const ta = Date.parse(a.last_opened_at || a.updated_at || "") || 0;
        const tb = Date.parse(b.last_opened_at || b.updated_at || "") || 0;
        return tb - ta;
      })
      .slice(0, 3);
  }, [writingList]);

  const topWriting = recentWriting[0] ?? null;
  const writingRecent = Boolean(
    topWriting &&
      isWithinHours(topWriting.last_opened_at || topWriting.updated_at, 72),
  );

  const evidenceCount = evidenceList?.count ?? 0;
  const themeCount = themes?.metrics.theme_count ?? 0;
  const assignedEvidence = themes?.metrics.assigned_evidence ?? 0;
  const conflictGaps = gaps?.metrics.by_type?.unexplained_conflict ?? 0;
  const gapCount = gaps?.metrics.gap_count ?? 0;
  const acceptedDecisions =
    decisions?.items.filter((d) => /accept|include|keep/i.test(d.type || d.label)).length ??
    0;

  const researchQuestion =
    hub?.open_questions[0]?.text ||
    hub?.project.instructions?.trim() ||
    hub?.project.description?.trim() ||
    null;

  const stage = deriveStage({
    paper: focusPaper,
    hasWriting: recentWriting.length > 0,
    writingRecent,
    evidenceCount,
    themeCount,
  });

  const lastActivityAt =
    hub?.unread_activity[0]?.at ||
    topWriting?.last_opened_at ||
    topWriting?.updated_at ||
    focusPaper?.created_at ||
    null;
  const lastActivityLabel = formatRelative(lastActivityAt);

  const totalPapers = data?.library.total_papers ?? 0;
  const analysed = data?.library.analysed ?? 0;
  const readCount = data?.library.read ?? 0;

  const funnel = useMemo(() => {
    const importPct = totalPapers > 0 ? 100 : 0;
    const readPct = totalPapers > 0 ? (readCount / totalPapers) * 100 : 0;
    const evidencePct =
      totalPapers > 0
        ? Math.min(100, ((analysed || 0) / totalPapers) * 100)
        : 0;
    // Writing: any draft with words = progress; active/draft status weighted
    let writingPct = 0;
    if (topWriting) {
      if (topWriting.word_count >= 800) writingPct = 70;
      else if (topWriting.word_count >= 200) writingPct = 45;
      else if (topWriting.word_count > 0) writingPct = 25;
      else writingPct = 10;
      if (topWriting.status === "active") writingPct = Math.min(100, writingPct + 15);
    }
    // Review: inverse of open gaps relative to evidence (honest approximation)
    let reviewPct = 0;
    if (evidenceCount > 0) {
      reviewPct = Math.max(0, 100 - (gapCount / Math.max(evidenceCount, 1)) * 100);
    } else if (analysed > 0) {
      reviewPct = 15;
    }
    return { importPct, readPct, evidencePct, writingPct, reviewPct };
  }, [
    totalPapers,
    readCount,
    analysed,
    topWriting,
    evidenceCount,
    gapCount,
  ]);

  const overallProgress = Math.round(
    (funnel.importPct +
      funnel.readPct +
      funnel.evidencePct +
      funnel.writingPct +
      funnel.reviewPct) /
      5,
  );

  const updateLines = useMemo(() => {
    if (!data) return [] as { text: string; href?: string }[];
    const lines: { text: string; href?: string }[] = [];

    const recentImports = data.recent_papers.filter((p) =>
      isWithinHours(p.created_at, 48),
    ).length;
    if (recentImports > 0) {
      lines.push({
        text: `${recentImports} new paper${recentImports === 1 ? "" : "s"} imported`,
        href: "/library",
      });
    }
    if (conflictGaps > 0) {
      lines.push({
        text: `${conflictGaps} unexplained conflict${conflictGaps === 1 ? "" : "s"} in evidence`,
        href: "/research/compare?tab=gaps",
      });
    }
    if (hub && hub.stats.open_questions > 0) {
      lines.push({
        text: `${hub.stats.open_questions} open research question${hub.stats.open_questions === 1 ? "" : "s"}`,
        href: currentProjectId ? `/projects/${currentProjectId}` : "/projects",
      });
    }
    if (topWriting && writingRecent) {
      lines.push({
        text: `Draft updated: ${topWriting.title || "Untitled"}`,
        href: `/writing?doc=${topWriting.id}`,
      });
    }
    if (hub && hub.pipeline_summary.failed > 0) {
      lines.push({
        text: `${hub.pipeline_summary.failed} analysis failure${hub.pipeline_summary.failed === 1 ? "" : "s"} need attention`,
        href: currentProjectId ? `/projects/${currentProjectId}` : "/library",
      });
    }
    if (data.library.unread > 0 && lines.length < 4) {
      lines.push({
        text: `${data.library.unread} unread paper${data.library.unread === 1 ? "" : "s"} waiting`,
        href: "/library?reading_status=unread",
      });
    }
    return lines.slice(0, 4);
  }, [data, conflictGaps, hub, topWriting, writingRecent, currentProjectId]);

  const priorityLine = useMemo(() => {
    if (conflictGaps > 0) return "Resolve unexplained evidence conflicts.";
    if (hub && hub.stats.open_questions > 0) return "Answer an open research question.";
    if (writingRecent && topWriting) return `Continue drafting “${topWriting.title || "Untitled"}”.`;
    if (focusPaper?.reading_status === "reading") {
      return `Continue reading “${focusPaper.title || focusPaper.name}”.`;
    }
    if (focusPaper) return `Continue work on “${focusPaper.title || focusPaper.name}”.`;
    return "Import or open a paper to begin.";
  }, [conflictGaps, hub, writingRecent, topWriting, focusPaper]);

  const projectName =
    hub?.project.name ??
    data?.projects.find((p) => p.id === currentProjectId)?.name ??
    null;

  const paperTitle = focusPaper
    ? focusPaper.title || focusPaper.name
    : "No active paper";

  return (
    <div className="scrollbar-thin h-full overflow-y-auto bg-background">
      <div className="mx-auto w-full max-w-[960px] px-5 py-5 sm:px-8">
        {isLoading ? (
          <HomeResearchSkeleton />
        ) : !data ? (
          <p className="text-sm text-muted-foreground">Could not load home.</p>
        ) : data.library.total_papers === 0 ? (
          <div className="py-12 text-center">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              Active research
            </p>
            <p className="mt-2 text-[22px] font-semibold tracking-tight">
              Start your research
            </p>
            <p className="mx-auto mt-2 max-w-sm text-[14px] text-muted-foreground">
              Import a paper. Dhund opens a research workspace — not a blank chat.
            </p>
            <Button className="mt-5 gap-2" onClick={() => navigate("/library#import")}>
              <Upload className="size-4" /> Import research
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header — no greeting theater */}
            <header>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                Active research
              </p>
              <h1 className="mt-1 text-[22px] font-semibold tracking-tight text-foreground sm:text-[24px]">
                Continue where you left off.
              </h1>
            </header>

            {/* Today's priority — subtle */}
            <div className="rounded-lg border border-border/80 bg-muted/30 px-3.5 py-2.5">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                Today&apos;s priority
              </p>
              <p className="mt-0.5 text-[13px] text-foreground">{priorityLine}</p>
            </div>

            {/* Hero — dense 70/30 */}
            <section className="rounded-xl border border-border bg-card">
              <div className="grid gap-0 md:grid-cols-[1.4fr_1fr]">
                <div className="space-y-3 border-b border-border p-4 md:border-b-0 md:border-r md:p-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-primary">
                      <span className="size-1.5 rounded-full bg-primary" aria-hidden />
                      Continue research
                    </span>
                    {projectName && (
                      <button
                        type="button"
                        onClick={() =>
                          currentProjectId && navigate(`/projects/${currentProjectId}`)
                        }
                        className="text-[11px] text-muted-foreground hover:text-foreground"
                      >
                        {projectName}
                      </button>
                    )}
                  </div>

                  <h2 className="text-[18px] font-semibold leading-snug tracking-tight sm:text-[20px]">
                    {paperTitle}
                  </h2>

                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                      Research question
                    </p>
                    <p className="mt-0.5 text-[13px] leading-snug text-foreground">
                      {researchQuestion ||
                        (currentProjectId
                          ? "Add an open question on the project to steer this card."
                          : "Open a project to attach a research question.")}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-x-6 gap-y-2 text-[12px]">
                    <div>
                      <p className="text-muted-foreground">Stage</p>
                      <p className="font-medium">{stage}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Last activity</p>
                      <p className="font-medium">{lastActivityLabel ?? "—"}</p>
                    </div>
                    {focusPaper && (
                      <div>
                        <p className="text-muted-foreground">AI</p>
                        <div className="pt-0.5">
                          <AiStateBadge
                            state={pipelineById.get(focusPaper.id)?.aiState}
                            metaStatus={focusPaper.meta_status}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  <Button
                    className="gap-1.5"
                    disabled={!focusPaper}
                    onClick={() =>
                      focusPaper && navigate(`/papers/${focusPaper.id}`)
                    }
                  >
                    Continue <ArrowRight className="size-3.5" />
                  </Button>
                </div>

                <div className="space-y-3 bg-muted/20 p-4 md:p-5">
                  <div>
                    <div className="mb-1 flex items-baseline justify-between">
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                        Progress
                      </p>
                      <p className="text-[13px] font-semibold tabular-nums text-foreground">
                        {overallProgress}%
                      </p>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${overallProgress}%` }}
                      />
                    </div>
                    <p className="mt-1 text-[10px] text-muted-foreground">
                      Approx. from import → read → evidence → writing → review
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-[12px]">
                    <div>
                      <p className="text-muted-foreground">Papers</p>
                      <p className="text-[16px] font-semibold tabular-nums">
                        {currentProjectId != null
                          ? (hub?.stats.papers ?? totalPapers)
                          : totalPapers}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Findings</p>
                      <p className="text-[16px] font-semibold tabular-nums">
                        {currentProjectId != null ? evidenceCount : "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Accepted</p>
                      <p className="text-[16px] font-semibold tabular-nums">
                        {currentProjectId != null
                          ? acceptedDecisions || assignedEvidence
                          : "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Conflicts</p>
                      <p className="text-[16px] font-semibold tabular-nums">
                        {currentProjectId != null ? conflictGaps : "—"}
                      </p>
                    </div>
                  </div>

                  {currentProjectId == null && (
                    <button
                      type="button"
                      onClick={() => navigate("/projects")}
                      className="text-[12px] font-medium text-primary hover:underline"
                    >
                      Select a project for evidence counts →
                    </button>
                  )}
                </div>
              </div>
            </section>

            {/* Research updates */}
            <section>
              <div className="mb-2 flex items-center justify-between">
                <SectionLabel>Research updates</SectionLabel>
                <button
                  type="button"
                  onClick={() => navigate("/library")}
                  className="text-[12px] text-muted-foreground hover:text-foreground"
                >
                  See all →
                </button>
              </div>
              <div className="rounded-xl border border-border bg-card px-3.5 py-3">
                {updateLines.length > 0 ? (
                  <ul className="space-y-2">
                    {updateLines.map((line) => (
                      <li key={line.text}>
                        <button
                          type="button"
                          onClick={() => line.href && navigate(line.href)}
                          className="flex w-full items-start gap-2 text-left text-[13px] text-foreground hover:text-primary"
                        >
                          <span
                            className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary"
                            aria-hidden
                          />
                          {line.text}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[13px] text-muted-foreground">
                    No new signals — open Library or Ask Dhund.
                  </p>
                )}
              </div>
            </section>

            {/* Research progress funnel */}
            <section>
              <SectionLabel>Research progress</SectionLabel>
              <div className="space-y-2.5 rounded-xl border border-border bg-card px-3.5 py-3.5">
                <ProgressBar label="Import" value={funnel.importPct} />
                <ProgressBar label="Read" value={funnel.readPct} />
                <ProgressBar label="Evidence" value={funnel.evidencePct} />
                <ProgressBar label="Writing" value={funnel.writingPct} />
                <ProgressBar label="Review" value={funnel.reviewPct} />
              </div>
            </section>

            {/* Continue working — primary first */}
            <section>
              <SectionLabel>Continue working</SectionLabel>
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => navigate("/library?provider=upload#import")}
                  className="flex w-full items-center gap-3 rounded-lg bg-primary px-4 py-3 text-left text-primary-foreground transition-opacity hover:opacity-90"
                >
                  <Plus className="size-4 shrink-0" />
                  <span className="flex-1 text-[13px] font-semibold">Upload papers</span>
                  <ArrowRight className="size-3.5 opacity-80" />
                </button>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  <button
                    type="button"
                    onClick={() => navigate("/chat")}
                    className="flex items-center gap-2 rounded-lg border border-border bg-card px-3.5 py-2.5 text-left text-[13px] font-medium hover:border-primary/40"
                  >
                    <MessageSquare className="size-4 text-primary" />
                    Ask Dhund
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate("/writing")}
                    className="flex items-center gap-2 rounded-lg border border-border bg-card px-3.5 py-2.5 text-left text-[13px] font-medium hover:border-primary/40"
                  >
                    <PenLine className="size-4 text-primary" />
                    Open writing
                  </button>
                  <button
                    type="button"
                    onClick={() => navigate("/library")}
                    className="flex items-center gap-2 rounded-lg border border-border bg-card px-3.5 py-2.5 text-left text-[13px] font-medium hover:border-primary/40"
                  >
                    <Library className="size-4 text-primary" />
                    Browse library
                  </button>
                </div>
              </div>
            </section>

            {/* Compact recent */}
            <section>
              <SectionLabel>Recent</SectionLabel>
              <div className="rounded-xl border border-border bg-card divide-y divide-border overflow-hidden">
                {data.recent_papers.slice(0, 4).map((p) => (
                  <button
                    key={`p-${p.id}`}
                    type="button"
                    onClick={() => navigate(`/papers/${p.id}`)}
                    className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-muted/30"
                  >
                    <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1 truncate text-[13px]">
                      {p.title || p.name}
                    </span>
                    <AiStateBadge
                      state={pipelineById.get(p.id)?.aiState}
                      metaStatus={p.meta_status}
                    />
                  </button>
                ))}
                {recentWriting.map((doc: WritingDocument) => (
                  <button
                    key={`w-${doc.id}`}
                    type="button"
                    onClick={() => navigate(`/writing?doc=${doc.id}`)}
                    className={cn(
                      "flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-muted/30",
                    )}
                  >
                    <PenLine className="size-3.5 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1 truncate text-[13px]">
                      {doc.title || "Untitled"}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {doc.word_count > 0 ? `${doc.word_count}w` : doc.status}
                    </span>
                  </button>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
