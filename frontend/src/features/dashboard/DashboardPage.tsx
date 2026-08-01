import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  FileText,
  FolderKanban,
  GitCompare,
  Library,
  MessageSquare,
  PenLine,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { HomeResearchSkeleton } from "@/components/common/ResearchSkeletons";
import { AiStateBadge, usePipelines, type AiStateResolved } from "@/features/pipeline";
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
    <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
      {children}
    </p>
  );
}

function timeGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function readingStageLabel(status: DashboardPaperBrief["reading_status"]): string {
  if (status === "reading") return "Reading";
  if (status === "read") return "Read";
  return "Unread";
}

function analysisStageLabel(meta: string): string {
  if (meta === "done") return "Analysed";
  if (meta === "running") return "Analysing";
  if (meta === "failed") return "Analysis failed";
  return "Queued";
}

function isWithinHours(iso: string | null, hours: number): boolean {
  if (!iso) return false;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return false;
  return Date.now() - t <= hours * 3600_000;
}

function ContinueCard({
  paper,
  projectName,
  onOpen,
  onOpenProject,
  aiState,
}: {
  paper: DashboardPaperBrief;
  projectName?: string | null;
  onOpen: () => void;
  onOpenProject?: () => void;
  aiState?: AiStateResolved;
}) {
  const title = paper.title || paper.name;
  const meta = [paper.authors?.split(";")[0]?.trim(), paper.year]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-primary">
          <span className="size-1.5 rounded-full bg-primary" aria-hidden />
          Continue research
        </span>
        {projectName && (
          <button
            type="button"
            onClick={onOpenProject}
            className="text-[11px] text-muted-foreground hover:text-foreground"
          >
            {projectName}
          </button>
        )}
      </div>
      <h2 className="mt-3 text-[22px] font-semibold leading-snug tracking-tight text-foreground sm:text-[24px]">
        {title}
      </h2>
      {meta && (
        <p className="mt-1.5 text-[13px] text-muted-foreground">{meta}</p>
      )}
      <div className="mt-4 flex flex-wrap gap-4 text-[12px]">
        <div>
          <p className="text-muted-foreground">Stage</p>
          <p className="font-medium text-foreground">
            {readingStageLabel(paper.reading_status)} · {analysisStageLabel(paper.meta_status)}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground">AI</p>
          <div className="pt-0.5">
            <AiStateBadge state={aiState} metaStatus={paper.meta_status} />
          </div>
        </div>
      </div>
      <div className="mt-5">
        <Button className="gap-1.5" onClick={onOpen}>
          Continue <ArrowRight className="size-3.5" />
        </Button>
      </div>
    </div>
  );
}

function NextAction({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-w-[140px] flex-1 items-center gap-2.5 rounded-lg border border-border bg-card px-3.5 py-3 text-left transition-colors hover:border-primary/40 hover:bg-muted/30"
    >
      <span className="text-primary">{icon}</span>
      <span className="text-[13px] font-medium text-foreground">{label}</span>
    </button>
  );
}

/** Launchpad = research control center (Projects remain at `/`). */
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

  const changeLines = useMemo(() => {
    if (!data) return [] as string[];
    const lines: string[] = [];
    const recentImports = data.recent_papers.filter((p) =>
      isWithinHours(p.created_at, 48),
    ).length;
    if (recentImports > 0) {
      lines.push(
        `${recentImports} paper${recentImports === 1 ? "" : "s"} imported in the last 48 hours`,
      );
    }
    if (data.library.unread > 0) {
      lines.push(
        `${data.library.unread} unread paper${data.library.unread === 1 ? "" : "s"} in your library`,
      );
    }
    const processing = data.library.processing ?? 0;
    if (processing > 0) {
      lines.push(
        `${processing} paper${processing === 1 ? "" : "s"} still processing`,
      );
    }
    if (hub) {
      if (hub.stats.open_questions > 0) {
        lines.push(
          `${hub.stats.open_questions} open question${hub.stats.open_questions === 1 ? "" : "s"} in ${hub.project.name}`,
        );
      }
      if (hub.pipeline_summary.failed > 0) {
        lines.push(
          `${hub.pipeline_summary.failed} analysis failure${hub.pipeline_summary.failed === 1 ? "" : "s"} in the active project`,
        );
      }
      if (hub.unread_activity.length > 0) {
        lines.push(
          `${hub.unread_activity.length} unread activity item${hub.unread_activity.length === 1 ? "" : "s"} in ${hub.project.name}`,
        );
      }
    }
    return lines.slice(0, 4);
  }, [data, hub]);

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

  const conflictGaps = gaps?.metrics.by_type?.unexplained_conflict ?? 0;
  const projectName =
    hub?.project.name ??
    data?.projects.find((p) => p.id === currentProjectId)?.name ??
    null;

  return (
    <div className="scrollbar-thin h-full overflow-y-auto bg-background">
      <div className="mx-auto w-full max-w-3xl px-5 py-6 sm:px-8">
        {isLoading ? (
          <HomeResearchSkeleton />
        ) : !data ? (
          <p className="text-sm text-muted-foreground">Could not load home.</p>
        ) : data.library.total_papers === 0 ? (
          <div className="px-1 py-14 text-center sm:py-16">
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              {timeGreeting()}
            </p>
            <p className="mt-2 text-[22px] font-semibold tracking-tight text-foreground">
              Start your research
            </p>
            <p className="mx-auto mt-2 max-w-sm text-[14px] leading-relaxed text-muted-foreground">
              Import a paper into your library. Dhund opens a research workspace — not a blank chat.
            </p>
            <Button className="mt-6 gap-2" onClick={() => navigate("/library#import")}>
              <Upload className="size-4" /> Import research
            </Button>
          </div>
        ) : (
          <div className="space-y-7">
            {/* 1. Greeting */}
            <header>
              <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Active research
              </p>
              <h1 className="mt-1 text-[28px] font-semibold tracking-tight text-foreground sm:text-[32px]">
                {timeGreeting()}.
              </h1>
              <p className="mt-1 text-[14px] text-muted-foreground">
                Continue your research.
              </p>
            </header>

            {/* 2. Continue research */}
            {focusPaper ? (
              <ContinueCard
                paper={focusPaper}
                projectName={projectName}
                aiState={pipelineById.get(focusPaper.id)?.aiState}
                onOpen={() => navigate(`/papers/${focusPaper.id}`)}
                onOpenProject={
                  currentProjectId
                    ? () => navigate(`/projects/${currentProjectId}`)
                    : undefined
                }
              />
            ) : (
              <div className="rounded-xl border border-border bg-card p-5">
                <p className="text-[14px] text-muted-foreground">
                  No focus paper yet — open your library to pick up where you left off.
                </p>
                <Button className="mt-3 gap-1.5" variant="outline" onClick={() => navigate("/library")}>
                  Open library <ArrowRight className="size-3.5" />
                </Button>
              </div>
            )}

            {/* 3. What changed */}
            <section>
              <SectionLabel>What changed</SectionLabel>
              <div className="rounded-xl border border-border bg-card px-4 py-3.5">
                {changeLines.length > 0 ? (
                  <ul className="space-y-2">
                    {changeLines.map((line) => (
                      <li
                        key={line}
                        className="flex gap-2 text-[13px] leading-snug text-foreground"
                      >
                        <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                        {line}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[13px] text-muted-foreground">
                    Nothing new since your last imports — open Library or Ask Dhund.
                  </p>
                )}
              </div>
            </section>

            {/* 4. Next actions */}
            <section>
              <SectionLabel>What&apos;s next</SectionLabel>
              <div className="flex flex-wrap gap-2">
                <NextAction
                  icon={<Upload className="size-4" />}
                  label="Upload"
                  onClick={() => navigate("/library?provider=upload#import")}
                />
                <NextAction
                  icon={<GitCompare className="size-4" />}
                  label="Evidence"
                  onClick={() => navigate("/research/compare?tab=matrix")}
                />
                <NextAction
                  icon={<PenLine className="size-4" />}
                  label="Writing"
                  onClick={() => navigate("/writing")}
                />
                <NextAction
                  icon={<MessageSquare className="size-4" />}
                  label="Ask Dhund"
                  onClick={() => navigate("/chat")}
                />
              </div>
            </section>

            {/* 5. Evidence snapshot */}
            <section>
              <SectionLabel>Evidence</SectionLabel>
              <div className="rounded-xl border border-border bg-card p-4">
                {currentProjectId == null ? (
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-[13px] text-muted-foreground">
                      Select a project to see themes, gaps, and conflicts.
                    </p>
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-1.5"
                      onClick={() => navigate("/projects")}
                    >
                      <FolderKanban className="size-3.5" /> Open projects
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-6">
                      <div>
                        <p className="text-[11px] text-muted-foreground">Themes</p>
                        <p className="text-[18px] font-semibold tabular-nums">
                          {themes?.metrics.theme_count ?? "—"}
                        </p>
                      </div>
                      <div>
                        <p className="text-[11px] text-muted-foreground">Gaps</p>
                        <p className="text-[18px] font-semibold tabular-nums">
                          {gaps?.metrics.gap_count ?? "—"}
                        </p>
                      </div>
                      <div>
                        <p className="text-[11px] text-muted-foreground">Conflicts</p>
                        <p className="text-[18px] font-semibold tabular-nums">
                          {gaps ? conflictGaps : "—"}
                        </p>
                      </div>
                      {themes?.metrics.assigned_evidence != null && (
                        <div>
                          <p className="text-[11px] text-muted-foreground">Assigned evidence</p>
                          <p className="text-[18px] font-semibold tabular-nums">
                            {themes.metrics.assigned_evidence}
                          </p>
                        </div>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => navigate("/research/compare?tab=matrix")}
                      className="inline-flex items-center gap-1 text-[13px] font-medium text-primary hover:underline"
                    >
                      Open evidence matrix <ArrowRight className="size-3.5" />
                    </button>
                  </div>
                )}
              </div>
            </section>

            {/* 6. Writing */}
            <section>
              <SectionLabel>Writing</SectionLabel>
              <div className="rounded-xl border border-border bg-card overflow-hidden">
                {currentProjectId == null ? (
                  <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3.5">
                    <p className="text-[13px] text-muted-foreground">
                      Writing docs are tied to a project.
                    </p>
                    <Button size="sm" variant="outline" onClick={() => navigate("/writing")}>
                      Open writing
                    </Button>
                  </div>
                ) : recentWriting.length === 0 ? (
                  <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3.5">
                    <p className="text-[13px] text-muted-foreground">No drafts yet.</p>
                    <Button size="sm" variant="outline" onClick={() => navigate("/writing")}>
                      Start writing
                    </Button>
                  </div>
                ) : (
                  recentWriting.map((doc: WritingDocument) => (
                    <button
                      key={doc.id}
                      type="button"
                      onClick={() => navigate(`/writing?doc=${doc.id}`)}
                      className="flex w-full items-center gap-3 border-b border-border px-4 py-3 text-left last:border-0 hover:bg-muted/30"
                    >
                      <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[13px] font-medium">{doc.title || "Untitled"}</p>
                        <p className="text-[12px] text-muted-foreground capitalize">
                          {doc.status}
                          {doc.word_count > 0 ? ` · ${doc.word_count} words` : ""}
                        </p>
                      </div>
                      <span className="text-[12px] font-medium text-primary">Continue</span>
                    </button>
                  ))
                )}
              </div>
            </section>

            {/* 7. Collections */}
            {(data.library.top_tags?.length ?? 0) > 0 && (
              <section>
                <SectionLabel>Collections</SectionLabel>
                <div className="flex flex-wrap gap-2">
                  {data.library.top_tags.slice(0, 8).map((t) => (
                    <button
                      key={t.tag}
                      type="button"
                      onClick={() =>
                        navigate(`/library?tag=${encodeURIComponent(t.tag)}`)
                      }
                      className="rounded-md border border-border bg-card px-2.5 py-1.5 text-[12px] text-foreground transition-colors hover:border-primary/40"
                    >
                      {t.tag}
                      <span className="ml-1.5 tabular-nums text-muted-foreground">{t.count}</span>
                    </button>
                  ))}
                </div>
              </section>
            )}

            {/* 8. Recent activity */}
            <section>
              <div className="mb-2 flex items-center justify-between">
                <SectionLabel>Recent activity</SectionLabel>
                <button
                  type="button"
                  onClick={() => navigate("/library")}
                  className="text-[12px] text-muted-foreground hover:text-foreground"
                >
                  Library
                </button>
              </div>
              <div className="rounded-xl border border-border bg-card divide-y divide-border overflow-hidden">
                {data.recent_papers.slice(0, 5).map((p) => (
                  <button
                    key={`paper-${p.id}`}
                    type="button"
                    onClick={() => navigate(`/papers/${p.id}`)}
                    className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/30"
                  >
                    <Library className="size-3.5 shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13px] font-medium">{p.title || p.name}</p>
                      <p className="truncate text-[12px] text-muted-foreground capitalize">
                        {p.reading_status}
                        {p.meta_status === "done" ? " · Analysed" : ""}
                      </p>
                    </div>
                    <AiStateBadge
                      state={pipelineById.get(p.id)?.aiState}
                      metaStatus={p.meta_status}
                    />
                  </button>
                ))}
                {data.recent_chats.slice(0, 3).map((c) => (
                  <button
                    key={`chat-${c.id}`}
                    type="button"
                    onClick={() =>
                      c.file_id
                        ? navigate(`/papers/${c.file_id}/chat/${c.id}`)
                        : navigate(`/c/${c.id}`)
                    }
                    className={cn(
                      "flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/30",
                    )}
                  >
                    <MessageSquare className="size-3.5 shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13px] font-medium">{c.title}</p>
                      <p className="text-[11px] text-muted-foreground">
                        {c.file_id != null ? "Paper chat" : "Conversation"}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </section>

            <div className="h-4" />
          </div>
        )}
      </div>
    </div>
  );
}
