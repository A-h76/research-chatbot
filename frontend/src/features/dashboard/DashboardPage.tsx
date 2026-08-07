/**
 * Research Launchpad — Home answers: "What research do you want to continue or start?"
 * Action-first (Anara interaction model), project-centric (Dhund identity). Not a metrics dashboard.
 */
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  FileText,
  FolderKanban,
  MessageSquare,
  PenLine,
  Search,
  Upload,
} from "lucide-react";
import { HomeResearchSkeleton } from "@/components/common/ResearchSkeletons";
import { useUI } from "@/context/UIContext";
import { writingApi } from "@/features/writing/api";
import { projectWritingUrl } from "@/features/projects/projectWorkspaceNav";
import { useDashboard } from "./useDashboard";
import { useMe } from "@/features/profile/useMe";
import { cn } from "@/lib/utils";

function greetingHour(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function QuickAction({
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
      className="flex flex-col items-start gap-3 rounded-lg border border-border/70 bg-card px-4 py-4 text-left transition-colors hover:border-border hover:bg-muted/40"
    >
      <span className="flex size-8 items-center justify-center rounded-md bg-muted/60 text-foreground/80">
        {icon}
      </span>
      <span className="text-[13px] font-medium tracking-tight text-foreground">{label}</span>
    </button>
  );
}

function HomeAssistant({
  firstName,
  onAsk,
}: {
  firstName: string;
  onAsk: () => void;
}) {
  return (
    <aside
      className="flex h-full min-h-0 w-full shrink-0 flex-col border-l border-border/50 bg-muted/15 lg:w-[280px]"
      aria-label="Research Assistant"
    >
      <div className="border-b border-border/40 px-4 py-3">
        <p className="text-[13px] font-semibold tracking-tight text-foreground">
          Research Assistant
        </p>
      </div>
      <div className="flex min-h-0 flex-1 flex-col px-4 py-4">
        <p className="text-[13px] leading-relaxed text-muted-foreground">
          {greetingHour()}
          {firstName ? `, ${firstName}` : ""}.
        </p>
        <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">
          What are you working on?
        </p>
        <div className="mt-auto pt-6">
          <button
            type="button"
            onClick={onAsk}
            className="flex w-full items-center gap-2 rounded-lg border border-border/70 bg-background px-3 py-2.5 text-left text-[13px] text-muted-foreground transition-colors hover:border-border hover:text-foreground"
          >
            <MessageSquare className="size-3.5 shrink-0 opacity-60" />
            Ask anything…
          </button>
        </div>
      </div>
    </aside>
  );
}

/** Adaptive Research Home — launchpad, not a dashboard. */
export function DashboardPage() {
  const navigate = useNavigate();
  const { currentProjectId, setCurrentProjectId } = useUI();
  const { data: me } = useMe();
  const { data, isLoading } = useDashboard();

  const firstName = (me?.name || "").trim().split(/\s+/)[0] || "";

  const writingProjectId = currentProjectId ?? data?.projects[0]?.id ?? null;

  const { data: writingList } = useQuery({
    queryKey: ["launchpad", "writing", writingProjectId],
    queryFn: () => writingApi.listDocuments(writingProjectId as number),
    enabled: writingProjectId != null,
    staleTime: 60_000,
  });

  const topWriting = useMemo(() => {
    const items = writingList?.items ?? [];
    if (!items.length) return null;
    return [...items].sort((a, b) => {
      const ta = Date.parse(a.last_opened_at || a.updated_at || "") || 0;
      const tb = Date.parse(b.last_opened_at || b.updated_at || "") || 0;
      return tb - ta;
    })[0];
  }, [writingList]);

  const recentProjects = data?.projects.slice(0, 5) ?? [];
  const unread = data?.library.unread ?? 0;

  const activity = useMemo(() => {
    const rows: { key: string; label: string; run: () => void }[] = [];
    if (topWriting && writingProjectId != null) {
      rows.push({
        key: "draft",
        label: `Continue “${topWriting.title || "Untitled draft"}”`,
        run: () => {
          setCurrentProjectId(writingProjectId);
          navigate(`${projectWritingUrl(writingProjectId)}?doc=${topWriting.id}`);
        },
      });
    }
    if (unread > 0) {
      rows.push({
        key: "unread",
        label: `${unread} unread paper${unread === 1 ? "" : "s"}`,
        run: () => navigate("/library?reading_status=unread"),
      });
    }
    if (currentProjectId != null) {
      rows.push({
        key: "evidence",
        label: "Review evidence",
        run: () => navigate(`/projects/${currentProjectId}/writing?focus=evidence`),
      });
    } else if (recentProjects[0]) {
      rows.push({
        key: "open-proj",
        label: `Open ${recentProjects[0].name}`,
        run: () => {
          setCurrentProjectId(recentProjects[0].id);
          navigate(`/projects/${recentProjects[0].id}`);
        },
      });
    }
    return rows.slice(0, 4);
  }, [
    topWriting,
    writingProjectId,
    unread,
    currentProjectId,
    recentProjects,
    navigate,
    setCurrentProjectId,
  ]);

  function openAsk() {
    if (currentProjectId != null) {
      navigate(`/projects/${currentProjectId}?tab=chat`);
    } else {
      navigate("/chat");
    }
  }

  function continueDraft() {
    if (topWriting && writingProjectId != null) {
      setCurrentProjectId(writingProjectId);
      navigate(`${projectWritingUrl(writingProjectId)}?doc=${topWriting.id}`);
      return;
    }
    if (writingProjectId != null) {
      setCurrentProjectId(writingProjectId);
      navigate(projectWritingUrl(writingProjectId));
      return;
    }
    navigate("/projects?new=1");
  }

  return (
    <div className="flex h-full min-h-0 overflow-hidden bg-background">
      <div className="scrollbar-thin min-h-0 min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-[720px] px-5 py-8 sm:px-8 sm:py-10">
          {isLoading ? (
            <HomeResearchSkeleton />
          ) : !data ? (
            <p className="text-sm text-muted-foreground">Could not load home.</p>
          ) : (
            <div className="space-y-10" data-density="low">
              <header>
                <h1 className="text-[26px] font-semibold tracking-tight text-foreground sm:text-[28px]">
                  {greetingHour()}
                  {firstName ? `, ${firstName}` : ""}
                </h1>
                <p className="mt-2 text-[15px] text-muted-foreground">
                  What would you like to work on today?
                </p>
              </header>

              <section aria-label="Quick actions">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <QuickAction
                    icon={<Upload className="size-4" strokeWidth={1.75} />}
                    label="Upload papers"
                    onClick={() => navigate("/library?upload=1#import")}
                  />
                  <QuickAction
                    icon={<FolderKanban className="size-4" strokeWidth={1.75} />}
                    label="New project"
                    onClick={() => navigate("/projects?new=1")}
                  />
                  <QuickAction
                    icon={<PenLine className="size-4" strokeWidth={1.75} />}
                    label="Continue writing"
                    onClick={continueDraft}
                  />
                  <QuickAction
                    icon={<Search className="size-4" strokeWidth={1.75} />}
                    label="Search literature"
                    onClick={() => navigate("/search")}
                  />
                </div>
              </section>

              <section aria-label="Recent projects">
                <div className="mb-3 flex items-baseline justify-between gap-2">
                  <h2 className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground/80">
                    Recent projects
                  </h2>
                  <button
                    type="button"
                    className="text-[12px] text-muted-foreground hover:text-foreground"
                    onClick={() => navigate("/projects")}
                  >
                    All projects
                  </button>
                </div>
                {recentProjects.length === 0 ? (
                  <button
                    type="button"
                    onClick={() => navigate("/projects?new=1")}
                    className="w-full rounded-lg border border-dashed border-border/80 px-4 py-6 text-left text-[13px] text-muted-foreground hover:border-border hover:text-foreground"
                  >
                    No projects yet — start one to organize papers and writing.
                  </button>
                ) : (
                  <ul className="divide-y divide-border/50 rounded-lg border border-border/60">
                    {recentProjects.map((p) => (
                      <li key={p.id}>
                        <button
                          type="button"
                          onClick={() => {
                            setCurrentProjectId(p.id);
                            navigate(`/projects/${p.id}`);
                          }}
                          className="flex w-full items-center gap-3 px-3.5 py-3 text-left transition-colors hover:bg-muted/40"
                        >
                          <span className="text-[15px]" aria-hidden>
                            {p.emoji || "📁"}
                          </span>
                          <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-foreground">
                            {p.name}
                          </span>
                          <span className="shrink-0 text-[12px] tabular-nums text-muted-foreground">
                            {p.paper_count} paper{p.paper_count === 1 ? "" : "s"}
                          </span>
                          <ArrowRight className="size-3.5 shrink-0 text-muted-foreground/50" />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              {activity.length > 0 ? (
                <section aria-label="Recent activity">
                  <h2 className="mb-3 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground/80">
                    Continue
                  </h2>
                  <ul className="space-y-1">
                    {activity.map((a) => (
                      <li key={a.key}>
                        <button
                          type="button"
                          onClick={a.run}
                          className={cn(
                            "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px]",
                            "text-foreground/90 hover:bg-muted/50",
                          )}
                        >
                          <FileText className="size-3.5 shrink-0 text-muted-foreground/60" />
                          <span className="min-w-0 flex-1 truncate">{a.label}</span>
                          <ArrowRight className="size-3.5 shrink-0 text-muted-foreground/40" />
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {data.library.total_papers === 0 && recentProjects.length === 0 ? (
                <p className="text-[13px] text-muted-foreground">
                  Upload papers or create a project — Dhund turns them into grounded writing.
                </p>
              ) : null}
            </div>
          )}
        </div>
      </div>

      <div className="hidden lg:flex">
        <HomeAssistant firstName={firstName} onAsk={openAsk} />
      </div>
    </div>
  );
}
