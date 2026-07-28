import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  FileText,
  FolderKanban,
  Library,
  MessageSquare,
  Quote,
  Upload,
  Wand2,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { AiStateBadge, usePipelines, type AiStateResolved } from "@/features/pipeline";
import { useDashboard } from "./useDashboard";
import { cn } from "@/lib/utils";
import type { DashboardPaperBrief, DashboardProject } from "./api";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
      {children}
    </p>
  );
}

function MetricRow({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-border py-2.5 last:border-0">
      <div>
        <p className="text-[13px] font-medium text-foreground">{label}</p>
        <p className="text-[12px] text-muted-foreground">{hint}</p>
      </div>
      <p className="text-[15px] font-semibold tabular-nums text-foreground">{value}</p>
    </div>
  );
}

function FocusCard({
  paper,
  onOpen,
  aiState,
}: {
  paper: DashboardPaperBrief;
  onOpen: () => void;
  aiState?: AiStateResolved;
}) {
  const title = paper.title || paper.name;
  const meta = [paper.authors?.split(";")[0]?.trim(), paper.year]
    .filter(Boolean)
    .join(" · ");

  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full items-center justify-between gap-4 rounded-lg border border-border bg-card px-4 py-3.5 text-left transition-colors hover:bg-muted/40"
    >
      <div className="min-w-0">
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Today&apos;s focus
        </p>
        <p className="mt-1 truncate text-[15px] font-semibold tracking-tight">{title}</p>
        <p className="mt-0.5 truncate text-[12px] text-muted-foreground">
          {meta || "Continue investigation"}
          {paper.meta_status === "done" ? " · Analysed" : ""}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <AiStateBadge state={aiState} metaStatus={paper.meta_status} />
        <span className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-[12px] font-medium text-primary-foreground">
          Continue <ArrowRight className="size-3.5" />
        </span>
      </div>
    </button>
  );
}

function PaperHero({
  paper,
  onOpen,
  aiState,
}: {
  paper: DashboardPaperBrief;
  onOpen: () => void;
  aiState?: AiStateResolved;
}) {
  const title = paper.title || paper.name;
  const meta = [paper.authors?.split(";")[0]?.trim(), paper.year, paper.meta_status === "done" ? "Ready" : null]
    .filter(Boolean)
    .join(" · ");

  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full flex-col gap-3 rounded-lg border border-border bg-card p-4 text-left transition-colors hover:border-primary/40 sm:flex-row sm:items-end sm:justify-between"
    >
      <div className="min-w-0 space-y-2">
        <p className="text-[11px] text-muted-foreground">Research workspace</p>
        <p className="text-[16px] font-semibold leading-snug tracking-tight">{title}</p>
        <p className="text-[12px] text-muted-foreground">{meta}</p>
        <div className="flex flex-wrap gap-4 pt-1">
          <div>
            <p className="text-[11px] text-muted-foreground">Analysis</p>
            <p className="text-[13px] font-medium">
              {paper.meta_status === "done" ? "Complete" : "In progress"}
            </p>
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground">Reading</p>
            <p className="text-[13px] font-medium capitalize">{paper.reading_status}</p>
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground">AI state</p>
            <div className="pt-0.5">
              <AiStateBadge state={aiState} metaStatus={paper.meta_status} />
            </div>
          </div>
        </div>
      </div>
      <span className="inline-flex shrink-0 items-center gap-1.5 rounded-md bg-primary px-3.5 py-2 text-[13px] font-medium text-primary-foreground">
        Open research workspace <ArrowRight className="size-3.5" />
      </span>
    </button>
  );
}

function ProjectRow({
  project,
  onClick,
}: {
  project: DashboardProject;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-3 border-b border-border px-1 py-2.5 text-left last:border-0 hover:bg-muted/30"
    >
      <span className="text-base leading-none">{project.emoji}</span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium">{project.name}</p>
        <p className="text-[12px] text-muted-foreground">
          {project.paper_count} paper{project.paper_count === 1 ? "" : "s"}
          {project.chat_count > 0
            ? ` · ${project.chat_count} research chat${project.chat_count === 1 ? "" : "s"}`
            : ""}
        </p>
      </div>
      <ArrowRight className="size-3.5 shrink-0 text-muted-foreground" />
    </button>
  );
}

function LaunchpadSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-20 w-full rounded-lg" />
      <Skeleton className="h-28 w-full rounded-lg" />
      <Skeleton className="h-40 w-full rounded-lg" />
    </div>
  );
}

/** Launchpad = research activity overview (Projects are home at `/`). */
export function DashboardPage() {
  const navigate = useNavigate();
  const { data, isLoading } = useDashboard();

  const focusPaper = useMemo(() => {
    if (!data) return null;
    return data.current_papers[0] ?? data.recent_papers.find((p) => p.meta_status === "done") ?? data.recent_papers[0] ?? null;
  }, [data]);

  const heroPaper = useMemo(() => {
    if (!data || !focusPaper) return null;
    const alt = data.recent_papers.find((p) => p.id !== focusPaper.id);
    return alt ?? focusPaper;
  }, [data, focusPaper]);

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

  const paperChats = data?.recent_chats.filter((c) => c.file_id != null).length ?? 0;

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-5 py-6 sm:px-8">
        <div className="mb-6">
          <h1 className="text-[20px] font-semibold tracking-tight">Continue research</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">
            One focus. Then your library&apos;s research state — not chat counts.
          </p>
        </div>

        {isLoading ? (
          <LaunchpadSkeleton />
        ) : !data ? (
          <p className="text-sm text-muted-foreground">Could not load home.</p>
        ) : data.library.total_papers === 0 ? (
          <div className="rounded-lg border border-dashed border-border px-4 py-10 text-center">
            <p className="text-[15px] font-medium">Start your library</p>
            <p className="mt-1 text-[13px] text-muted-foreground">
              Upload a paper to open a research workspace.
            </p>
            <Button className="mt-4 gap-2" onClick={() => navigate("/library")}>
              <Upload className="size-4" /> Upload paper
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            {focusPaper && (
              <FocusCard
                paper={focusPaper}
                aiState={pipelineById.get(focusPaper.id)?.aiState}
                onOpen={() => navigate(`/papers/${focusPaper.id}`)}
              />
            )}

            <section>
              <SectionLabel>Today in your library</SectionLabel>
              <div className="rounded-lg border border-border bg-card px-4">
                <MetricRow
                  label="Papers analysed"
                  value={data.library.analysed ?? 0}
                  hint="Structure · classify · evidence ready"
                />
                <MetricRow
                  label="Still processing"
                  value={data.library.processing ?? 0}
                  hint="Queued or running pipeline"
                />
                <MetricRow
                  label="Currently reading"
                  value={data.library.reading}
                  hint="Marked in progress"
                />
                <MetricRow
                  label="Paper conversations"
                  value={paperChats}
                  hint="Recent research chats on papers"
                />
              </div>
            </section>

            {heroPaper && (
              <section>
                <SectionLabel>Research workspace</SectionLabel>
                <PaperHero
                  paper={heroPaper}
                  aiState={pipelineById.get(heroPaper.id)?.aiState}
                  onOpen={() => navigate(`/papers/${heroPaper.id}`)}
                />
              </section>
            )}

            <section>
              <SectionLabel>Quick actions</SectionLabel>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" className="gap-1.5" onClick={() => navigate("/library")}>
                  <Upload className="size-3.5" /> Upload paper
                </Button>
                {focusPaper && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-1.5"
                    onClick={() => navigate(`/papers/${focusPaper.id}?tab=evidence`)}
                  >
                    <FileText className="size-3.5" /> Open Evidence
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1.5"
                  onClick={() => navigate("/writing")}
                >
                  <Wand2 className="size-3.5" /> Continue writing
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1.5"
                  onClick={() => navigate("/projects")}
                >
                  <FolderKanban className="size-3.5" /> Open project
                </Button>
              </div>
            </section>

            {data.projects.length > 0 && (
              <section>
                <div className="mb-2 flex items-center justify-between">
                  <SectionLabel>Projects</SectionLabel>
                  <button
                    type="button"
                    onClick={() => navigate("/projects")}
                    className="text-[12px] text-muted-foreground hover:text-foreground"
                  >
                    View all
                  </button>
                </div>
                <div className="rounded-lg border border-border bg-card px-3">
                  {data.projects.slice(0, 4).map((p) => (
                    <ProjectRow
                      key={p.id}
                      project={p}
                      onClick={() => navigate(`/projects/${p.id}`)}
                    />
                  ))}
                </div>
              </section>
            )}

            <section>
              <div className="mb-2 flex items-center justify-between">
                <SectionLabel>Recent papers</SectionLabel>
                <button
                  type="button"
                  onClick={() => navigate("/library")}
                  className="text-[12px] text-muted-foreground hover:text-foreground"
                >
                  Library
                </button>
              </div>
              <div className="rounded-lg border border-border bg-card divide-y divide-border overflow-hidden">
                {data.recent_papers.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => navigate(`/papers/${p.id}`)}
                    className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/40"
                  >
                    <Library className="size-3.5 shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13px] font-medium">
                        {p.title || p.name}
                      </p>
                      <p className="truncate text-[12px] text-muted-foreground">
                        {[p.authors?.split(";")[0]?.trim(), p.year]
                          .filter(Boolean)
                          .join(" · ") || "No metadata yet"}
                      </p>
                    </div>
                    <AiStateBadge
                      state={pipelineById.get(p.id)?.aiState}
                      metaStatus={p.meta_status}
                    />
                  </button>
                ))}
              </div>
            </section>

            {data.recent_chats.length > 0 && (
              <section>
                <SectionLabel>Recent conversations</SectionLabel>
                <div className="rounded-lg border border-border bg-card divide-y divide-border overflow-hidden">
                  {data.recent_chats.slice(0, 4).map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() =>
                        c.file_id
                          ? navigate(`/papers/${c.file_id}/chat/${c.id}`)
                          : navigate(`/c/${c.id}`)
                      }
                      className={cn(
                        "flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/40",
                      )}
                    >
                      <MessageSquare className="size-3.5 shrink-0 text-muted-foreground" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[13px] font-medium">{c.title}</p>
                        {c.file_id != null && (
                          <p className="text-[11px] text-muted-foreground">Paper chat</p>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </section>
            )}

            {data.recent_citations.length > 0 && (
              <section>
                <SectionLabel>Recent citations</SectionLabel>
                <div className="rounded-lg border border-border bg-card divide-y divide-border overflow-hidden">
                  {data.recent_citations.slice(0, 3).map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => navigate("/citations")}
                      className="flex w-full items-start gap-3 px-3 py-2.5 text-left hover:bg-muted/40"
                    >
                      <Quote className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
                      <div className="min-w-0">
                        <p className="truncate text-[13px] font-medium">
                          {c.title || "Untitled"}
                        </p>
                        <p className="truncate text-[12px] text-muted-foreground">
                          {[c.authors?.split(";")[0]?.trim(), c.year]
                            .filter(Boolean)
                            .join(", ")}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </section>
            )}

            <div className="h-4" />
          </div>
        )}
      </div>
    </div>
  );
}
