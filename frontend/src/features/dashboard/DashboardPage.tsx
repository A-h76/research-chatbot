/**
 * Home — Product Constitution: one question.
 * "What should I do next?"
 * Greeting → context → recommendation. Not a launchpad dashboard.
 */
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { HomeResearchSkeleton } from "@/components/common/ResearchSkeletons";
import { useUI } from "@/context/UIContext";
import { assistantApi } from "@/features/assistant/api";
import { useMe } from "@/features/profile/useMe";
import { useDashboard } from "./useDashboard";
import { buildHomeViewModel } from "./homeViewModel";
import { HomeAssistantPanel } from "./components/HomeAssistantPanel";

function greetingHour(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { currentProjectId, setCurrentProjectId } = useUI();
  const { data: me } = useMe();
  const { data, isLoading } = useDashboard();

  const firstName = (me?.name || "").trim().split(/\s+/)[0] || "";

  const stateQ = useQuery({
    queryKey: ["assistant", "research-state", "home", currentProjectId],
    queryFn: () => assistantApi.researchState(currentProjectId),
    staleTime: 45_000,
    enabled: me != null,
  });

  // Still show Home while state loads; fall back to dashboard signals.
  const view = buildHomeViewModel(stateQ.data, {
    unread: data?.library.unread ?? 0,
    hasProject: (data?.projects.length ?? 0) > 0,
  });

  const currentProject =
    currentProjectId != null
      ? data?.projects.find((p) => p.id === currentProjectId)
      : data?.projects[0];

  const projectTitle =
    view.projectTitle || currentProject?.name || null;

  return (
    <div className="flex h-full min-h-0 overflow-hidden bg-background">
      <div className="scrollbar-thin min-h-0 min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex min-h-full w-full max-w-[560px] flex-col justify-center px-5 py-12 sm:px-8 sm:py-16">
          {isLoading && !data ? (
            <HomeResearchSkeleton />
          ) : !data ? (
            <p className="text-sm text-muted-foreground">Could not load home.</p>
          ) : (
            <div className="space-y-10" data-density="low">
              <header className="space-y-3">
                <h1 className="text-[26px] font-semibold tracking-tight text-foreground sm:text-[28px]">
                  {greetingHour()}
                  {firstName ? `, ${firstName}` : ""}
                  .
                </h1>
                {projectTitle ? (
                  <p className="text-[15px] leading-relaxed text-muted-foreground">
                    You&apos;re working on{" "}
                    <span className="font-medium text-foreground">{projectTitle}</span>.
                  </p>
                ) : (
                  <p className="text-[15px] leading-relaxed text-muted-foreground">
                    You&apos;re just getting started — let&apos;s build momentum.
                  </p>
                )}
                {view.lede ? (
                  <p className="text-[15px] leading-relaxed text-muted-foreground">
                    Today&apos;s next step is {view.lede}.
                  </p>
                ) : null}
              </header>

              <section aria-label="Next step" className="space-y-4">
                <p className="text-[12px] font-medium uppercase tracking-[0.08em] text-muted-foreground/80">
                  {view.status}
                </p>

                <button
                  type="button"
                  onClick={() => navigate(view.href)}
                  className="group w-full rounded-xl border border-primary/25 bg-primary/[0.04] px-5 py-5 text-left transition-colors hover:border-primary/40 hover:bg-primary/[0.07]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1.5">
                      <p className="text-[17px] font-semibold tracking-tight text-foreground">
                        {view.recommendation}
                      </p>
                      <p className="text-[13px] leading-relaxed text-muted-foreground">
                        {view.detail}
                      </p>
                      {view.context ? (
                        <p className="pt-1 text-[12px] tabular-nums text-muted-foreground/90">
                          {view.context}
                        </p>
                      ) : null}
                    </div>
                    <ArrowRight className="mt-1 size-4 shrink-0 text-primary transition-transform group-hover:translate-x-0.5" />
                  </div>
                </button>
              </section>

              <footer className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[12px] text-muted-foreground">
                {currentProject ? (
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 font-medium text-foreground/80 hover:text-foreground"
                    onClick={() => {
                      setCurrentProjectId(currentProject.id);
                      navigate(`/projects/${currentProject.id}`);
                    }}
                  >
                    Continue project
                    <ArrowRight className="size-3 opacity-70" aria-hidden />
                  </button>
                ) : (
                  <Link
                    to="/projects?new=1"
                    className="inline-flex items-center gap-1 font-medium text-foreground/80 hover:text-foreground"
                  >
                    Start a project
                    <ArrowRight className="size-3 opacity-70" aria-hidden />
                  </Link>
                )}
                <span className="text-border" aria-hidden>
                  ·
                </span>
                <Link to="/library" className="hover:text-foreground">
                  Library
                </Link>
                <span className="text-border" aria-hidden>
                  ·
                </span>
                <Link to="/projects" className="hover:text-foreground">
                  All projects
                </Link>
              </footer>
            </div>
          )}
        </div>
      </div>

      <div className="hidden lg:flex">
        <HomeAssistantPanel firstName={firstName} />
      </div>
    </div>
  );
}
