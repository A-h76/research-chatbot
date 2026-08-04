import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpen,
  FileText,
  FolderKanban,
  MessageSquare,
  PenLine,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { HomeResearchSkeleton } from "@/components/common/ResearchSkeletons";
import { AiStateBadge, usePipelines } from "@/features/pipeline";
import { useUI } from "@/context/UIContext";
import { useProjectHub } from "@/features/projects/useProjects";
import { evidenceApi } from "@/features/evidence/api";
import { writingApi } from "@/features/writing/api";
import { useDashboard } from "./useDashboard";
import { useMe } from "@/features/profile/useMe";
import { HomeHeroUpload } from "./components/HomeHeroUpload";
import { HomeSecondaryActions } from "./components/HomeSecondaryActions";
import { GettingStartedChecklist } from "./components/GettingStartedChecklist";
import { HomeRecentList, HomeSectionLabel } from "./components/HomeRecentList";
import {
  ResearchOsHeroFlow,
  ResearchEcosystemCloud,
} from "@/features/research-flow";
import {
  buildGettingStarted,
  deriveHomeStage,
  literatureReviews,
} from "./homeMaturity";
import type { WritingDocument } from "@/types/api";

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

function isWithinHours(iso: string | null | undefined, hours: number): boolean {
  if (!iso) return false;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return false;
  return Date.now() - t <= hours * 3600_000;
}

/** Adaptive Research Home — Stage 1 new user → Stage 3 active researcher. */
export function DashboardPage() {
  const navigate = useNavigate();
  const { currentProjectId } = useUI();
  const { data: me } = useMe();
  const { data, isLoading } = useDashboard();
  const { data: hub } = useProjectHub(currentProjectId);

  const firstName = (me?.name || "").trim().split(/\s+/)[0] || "";
  const focusLabel =
    me?.onboarding?.institution?.trim() ||
    me?.onboarding?.research_focus?.trim() ||
    "";
  const fieldLabels = (me?.onboarding?.research_fields || [])
    .map(
      (id) =>
        (
          {
            ai: "Artificial Intelligence",
            medicine: "Medicine",
            physics: "Physics",
            economics: "Economics",
            biology: "Biology",
            chemistry: "Chemistry",
            cs: "Computer Science",
            engineering: "Engineering",
            social: "Social Sciences",
            other: "Other",
          } as Record<string, string>
        )[id] || id,
    )
    .slice(0, 3);
  const researchFocusLine =
    fieldLabels.length > 0 ? fieldLabels.join(" · ") : focusLabel;

  const writingProjectId =
    currentProjectId ?? data?.projects[0]?.id ?? null;

  const { data: writingList } = useQuery({
    queryKey: ["launchpad", "writing", writingProjectId],
    queryFn: () => writingApi.listDocuments(writingProjectId as number),
    enabled: writingProjectId != null,
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

  const recentWriting = useMemo(() => {
    const items = writingList?.items ?? [];
    return [...items]
      .sort((a, b) => {
        const ta = Date.parse(a.last_opened_at || a.updated_at || "") || 0;
        const tb = Date.parse(b.last_opened_at || b.updated_at || "") || 0;
        return tb - ta;
      })
      .slice(0, 5);
  }, [writingList]);

  const litReviews = useMemo(
    () => literatureReviews(recentWriting).slice(0, 4),
    [recentWriting],
  );

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

  const stage = useMemo(() => {
    if (!data) return 1 as const;
    return deriveHomeStage({
      totalPapers: data.library.total_papers,
      projectCount: data.projects.length,
      chatCount: data.recent_chats.length,
      analysed: data.library.analysed ?? 0,
      writingCount: recentWriting.length,
    });
  }, [data, recentWriting.length]);

  const checklist = useMemo(
    () => (data ? buildGettingStarted(data) : []),
    [data],
  );

  const conflictGaps = gaps?.metrics.by_type?.unexplained_conflict ?? 0;
  const evidenceCount = evidenceList?.count ?? 0;
  const topWriting = recentWriting[0] ?? null;
  const writingRecent = Boolean(
    topWriting &&
      isWithinHours(topWriting.last_opened_at || topWriting.updated_at, 72),
  );

  const priorityLine = useMemo(() => {
    if (conflictGaps > 0) return "Resolve unexplained evidence conflicts.";
    if (hub && hub.stats.open_questions > 0) return "Answer an open research question.";
    if (writingRecent && topWriting) {
      return `Continue drafting “${topWriting.title || "Untitled"}”.`;
    }
    if (focusPaper?.reading_status === "reading") {
      return `Continue reading “${focusPaper.title || focusPaper.name}”.`;
    }
    if (focusPaper) {
      return `Continue work on “${focusPaper.title || focusPaper.name}”.`;
    }
    return "Open a paper or start a project to continue.";
  }, [conflictGaps, hub, writingRecent, topWriting, focusPaper]);

  const insightLines = useMemo(() => {
    if (!data) return [] as { text: string; href?: string }[];
    const lines: { text: string; href?: string }[] = [];
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
    if (evidenceCount > 0) {
      lines.push({
        text: `${evidenceCount} evidence item${evidenceCount === 1 ? "" : "s"} ready to cite`,
        href: currentProjectId ? `/projects/${currentProjectId}` : "/library",
      });
    }
    if (data.library.unread > 0) {
      lines.push({
        text: `${data.library.unread} unread paper${data.library.unread === 1 ? "" : "s"} waiting`,
        href: "/library?reading_status=unread",
      });
    }
    return lines.slice(0, 4);
  }, [data, conflictGaps, hub, evidenceCount, currentProjectId]);

  const writingPct = useMemo(() => {
    if (!topWriting) return 0;
    let pct = 10;
    if (topWriting.word_count >= 800) pct = 70;
    else if (topWriting.word_count >= 200) pct = 45;
    else if (topWriting.word_count > 0) pct = 25;
    if (topWriting.status === "active") pct = Math.min(100, pct + 15);
    return pct;
  }, [topWriting]);

  const projectName =
    hub?.project.name ??
    data?.projects.find((p) => p.id === currentProjectId)?.name ??
    null;

  return (
    <div className="scrollbar-thin h-full overflow-y-auto bg-background">
      <div className="mx-auto w-full max-w-[960px] px-5 py-5 sm:px-8">
        {isLoading ? (
          <HomeResearchSkeleton />
        ) : !data ? (
          <p className="text-sm text-foreground/65">Could not load home.</p>
        ) : stage === 1 ? (
          <div className="space-y-6 py-6 sm:py-8" data-density="low">
            <header>
              <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
                What should I do next?
              </p>
              <h1 className="mt-1.5 text-[24px] font-semibold tracking-tight text-foreground">
                {firstName ? `Welcome, ${firstName}` : "Welcome to Dhund"}
              </h1>
              {researchFocusLine ? (
                <p className="mt-2 text-[14px] text-muted-foreground">
                  Research focus · {researchFocusLine}
                </p>
              ) : (
                <p className="mt-2 text-[14px] text-muted-foreground">
                  Start with your first paper — everything else follows from evidence.
                </p>
              )}
            </header>

            <div className="grid gap-3 lg:grid-cols-[1.35fr_1fr] lg:items-start">
              <HomeHeroUpload />
              <HomeSecondaryActions />
            </div>

            <GettingStartedChecklist items={checklist} />

            <details className="group rounded-md border border-border">
              <summary className="cursor-pointer list-none px-3.5 py-2.5 text-[13px] font-medium text-muted-foreground marker:content-none hover:text-foreground [&::-webkit-details-marker]:hidden">
                How Dhund works · Research ecosystem
              </summary>
              <div className="space-y-4 border-t border-border px-3.5 py-3">
                <ResearchOsHeroFlow />
                <div>
                  <p className="text-[12px] text-muted-foreground">
                    Connect the tools you already use — Dhund unifies them into one evidence pipeline.
                  </p>
                  <ResearchEcosystemCloud className="mt-2" compact showCategories={false} />
                </div>
              </div>
            </details>
          </div>
        ) : (
          <div className="space-y-5 py-2" data-density="medium">
            <header>
              <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
                What should I do next?
              </p>
              <h1 className="mt-1.5 text-[22px] font-semibold tracking-tight text-foreground sm:text-[24px]">
                {stage === 3
                  ? firstName
                    ? `Resume your research, ${firstName}`
                    : "Resume your research"
                  : firstName
                    ? `Continue your research, ${firstName}`
                    : "Continue your research"}
              </h1>
              {researchFocusLine ? (
                <p className="mt-1.5 text-[13px] text-muted-foreground">
                  Research focus · {researchFocusLine}
                </p>
              ) : null}
            </header>

            {/* Single primary answer — Next + Continue merged (Cognitive Load Doctrine) */}
            <section className="rounded-md border border-border bg-card p-4 sm:p-5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-primary">
                  <span className="size-1.5 rounded-full bg-primary" aria-hidden />
                  Next
                </span>
                {projectName ? (
                  <button
                    type="button"
                    onClick={() =>
                      currentProjectId && navigate(`/projects/${currentProjectId}`)
                    }
                    className="text-[11px] text-muted-foreground hover:text-foreground"
                  >
                    {projectName}
                  </button>
                ) : null}
              </div>
              <p className="mt-2 text-[14px] leading-snug text-foreground">{priorityLine}</p>
              <h2 className="mt-3 text-[17px] font-semibold leading-snug tracking-tight sm:text-[18px]">
                {focusPaper
                  ? focusPaper.title || focusPaper.name
                  : topWriting
                    ? topWriting.title || "Untitled draft"
                    : "Pick up where you left off"}
              </h2>
              {insightLines[0] ? (
                <button
                  type="button"
                  onClick={() => insightLines[0].href && navigate(insightLines[0].href)}
                  className="mt-2 text-left text-[12px] text-muted-foreground hover:text-primary"
                >
                  {insightLines[0].text}
                </button>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-2">
                <Button
                  className="gap-1.5"
                  disabled={!focusPaper && !topWriting}
                  onClick={() => {
                    if (focusPaper) navigate(`/papers/${focusPaper.id}`);
                    else if (topWriting) navigate(`/writing?doc=${topWriting.id}`);
                  }}
                >
                  Continue <ArrowRight className="size-3.5" />
                </Button>
                <Button
                  variant="outline"
                  onClick={() => navigate("/library?upload=1#import")}
                >
                  Upload paper
                </Button>
              </div>
            </section>

            {stage === 3 ? (
              <>
                <section>
                  <HomeSectionLabel>Active projects</HomeSectionLabel>
                  <HomeRecentList
                    empty="No projects yet — start one to organize evidence and writing."
                    items={data.projects.slice(0, 5).map((p) => ({
                      key: `proj-${p.id}`,
                      label: `${p.emoji ? `${p.emoji} ` : ""}${p.name}`,
                      meta: `${p.paper_count} papers`,
                      icon: FolderKanban,
                      onClick: () => navigate(`/projects/${p.id}`),
                    }))}
                  />
                </section>

                {(litReviews.length > 0 || recentWriting.length > 0) && (
                  <section>
                    <HomeSectionLabel>
                      {litReviews.length > 0
                        ? "Literature reviews in progress"
                        : "Writing in progress"}
                    </HomeSectionLabel>
                    <div className="space-y-2">
                      {topWriting ? (
                        <div className="rounded-md border border-border bg-card px-3.5 py-3">
                          <button
                            type="button"
                            onClick={() => navigate(`/writing?doc=${topWriting.id}`)}
                            className="flex w-full items-center gap-2 text-left"
                          >
                            <PenLine className="size-3.5 text-muted-foreground" />
                            <span className="min-w-0 flex-1 truncate text-[13px] font-medium">
                              {topWriting.title || "Untitled"}
                            </span>
                            <span className="text-[11px] tabular-nums text-muted-foreground">
                              {topWriting.word_count}w
                            </span>
                          </button>
                          <div className="mt-2.5 h-px w-full overflow-hidden bg-border">
                            <div
                              className="h-px bg-primary transition-all duration-300"
                              style={{ width: `${writingPct}%` }}
                              aria-hidden
                            />
                          </div>
                        </div>
                      ) : null}
                      <HomeRecentList
                        empty="No other drafts yet."
                        items={(litReviews.length > 0 ? litReviews : recentWriting.slice(0, 3))
                          .filter((d) => d.id !== topWriting?.id)
                          .map((doc: WritingDocument) => ({
                            key: `w-${doc.id}`,
                            label: doc.title || "Untitled",
                            meta: formatRelative(doc.last_opened_at || doc.updated_at) ?? undefined,
                            icon: BookOpen,
                            onClick: () => navigate(`/writing?doc=${doc.id}`),
                          }))}
                      />
                    </div>
                  </section>
                )}

                <section>
                  <HomeSectionLabel>Recently opened</HomeSectionLabel>
                  <HomeRecentList
                    empty="Nothing opened recently."
                    items={[
                      ...data.recent_papers.slice(0, 3).map((p) => ({
                        key: `rp-${p.id}`,
                        label: p.title || p.name,
                        meta: formatRelative(p.created_at) ?? undefined,
                        icon: FileText,
                        onClick: () => navigate(`/papers/${p.id}`),
                      })),
                      ...data.recent_chats.slice(0, 2).map((c) => ({
                        key: `rc-${c.id}`,
                        label: c.title,
                        meta: formatRelative(c.updated_at) ?? undefined,
                        icon: MessageSquare,
                        onClick: () => navigate(`/c/${c.id}`),
                      })),
                    ]}
                  />
                </section>
              </>
            ) : (
              <>
                <section>
                  <HomeSectionLabel>Recent papers</HomeSectionLabel>
                  <div className="divide-y divide-border overflow-hidden rounded-md border border-border bg-card">
                    {data.recent_papers.length === 0 ? (
                      <p className="px-3.5 py-4 text-[13px] text-muted-foreground">
                        No papers yet — upload to start.
                      </p>
                    ) : (
                      data.recent_papers.slice(0, 5).map((p) => (
                        <button
                          key={`p-${p.id}`}
                          type="button"
                          onClick={() => navigate(`/papers/${p.id}`)}
                          className="flex w-full items-center gap-3 px-3.5 py-2.5 text-left transition-colors duration-150 hover:bg-muted/40"
                        >
                          <FileText className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                          <span className="min-w-0 flex-1 truncate text-[13px] text-foreground">
                            {p.title || p.name}
                          </span>
                          <AiStateBadge
                            state={pipelineById.get(p.id)?.aiState}
                            metaStatus={p.meta_status}
                          />
                        </button>
                      ))
                    )}
                  </div>
                </section>

                <section>
                  <HomeSectionLabel>Context</HomeSectionLabel>
                  <HomeRecentList
                    empty="Create a project, ask Dhund, or start a literature review."
                    items={[
                      ...data.projects.slice(0, 2).map((p) => ({
                        key: `proj-${p.id}`,
                        label: `${p.emoji ? `${p.emoji} ` : ""}${p.name}`,
                        meta: `${p.paper_count} papers`,
                        icon: FolderKanban,
                        onClick: () => navigate(`/projects/${p.id}`),
                      })),
                      ...(litReviews.length > 0 ? litReviews : recentWriting)
                        .slice(0, 2)
                        .map((doc) => ({
                          key: `lr-${doc.id}`,
                          label: doc.title || "Untitled",
                          meta: formatRelative(doc.last_opened_at || doc.updated_at) ?? undefined,
                          icon: BookOpen,
                          onClick: () => navigate(`/writing?doc=${doc.id}`),
                        })),
                      ...data.recent_chats.slice(0, 2).map((c) => ({
                        key: `c-${c.id}`,
                        label: c.title,
                        meta: formatRelative(c.updated_at) ?? undefined,
                        icon: MessageSquare,
                        onClick: () => navigate(`/c/${c.id}`),
                      })),
                    ]}
                  />
                </section>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
