/**
 * Home — Product Constitution: one question.
 * "What should I do next?"
 * Greeting → context → recommendation. Not a launchpad dashboard.
 *
 * Typography: text-primary / secondary / tertiary / accent (see index.css).
 */
import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { HomeResearchSkeleton } from "@/components/common/ResearchSkeletons";
import { useUI } from "@/context/UIContext";
import { assistantApi } from "@/features/assistant/api";
import { useMe } from "@/features/profile/useMe";
import { cn } from "@/lib/utils";
import { useDashboard } from "./useDashboard";
import { buildHomeViewModel } from "./homeViewModel";
import { HomeAssistantPanel } from "./components/HomeAssistantPanel";
import { greetingHour } from "./mentorOpening";

export function DashboardPage() {
  const navigate = useNavigate();
  const { currentProjectId, setCurrentProjectId } = useUI();
  const { data: me } = useMe();
  const { data, isLoading } = useDashboard();

  const firstName = (me?.name || "").trim().split(/\s+/)[0] || "";

  // One project identity for Home + Mentor — never invent different realities.
  const homeProjectId = currentProjectId ?? data?.projects[0]?.id ?? null;
  const homeProject =
    homeProjectId != null
      ? data?.projects.find((p) => p.id === homeProjectId) ?? null
      : null;

  useEffect(() => {
    if (currentProjectId == null && homeProjectId != null) {
      setCurrentProjectId(homeProjectId);
    }
  }, [currentProjectId, homeProjectId, setCurrentProjectId]);

  const stateQ = useQuery({
    queryKey: ["assistant", "research-state", "home", homeProjectId],
    queryFn: () => assistantApi.researchState(homeProjectId),
    staleTime: 45_000,
    enabled: me != null,
  });

  const view = buildHomeViewModel(stateQ.data, {
    unread: data?.library.unread ?? 0,
    hasProject: (data?.projects.length ?? 0) > 0,
    projectTitle: homeProject?.name ?? null,
  });

  const projectTitle = view.projectTitle || homeProject?.name || null;

  return (
    <div className="flex h-full min-h-0 overflow-hidden bg-background">
      <div className="scrollbar-thin min-h-0 min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex min-h-full w-full max-w-[560px] flex-col justify-center px-5 py-12 sm:px-8 sm:py-16">
          {isLoading && !data ? (
            <HomeResearchSkeleton />
          ) : !data ? (
            <p className="text-sm text-text-secondary">Could not load home.</p>
          ) : (
            <div className="space-y-10" data-density="low">
              <header className="space-y-3 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-500">
                <h1 className="text-[26px] font-semibold tracking-tight text-text-primary sm:text-[28px]">
                  {greetingHour()}
                  {firstName ? `, ${firstName}` : ""}
                  .
                </h1>
                {projectTitle ? (
                  <p className="text-[15px] leading-relaxed text-text-secondary">
                    You&apos;re working on{" "}
                    <span className="font-medium text-text-primary">{projectTitle}</span>.
                  </p>
                ) : (
                  <p className="text-[15px] leading-relaxed text-text-secondary">
                    You&apos;re just getting started — let&apos;s build momentum.
                  </p>
                )}
                {view.milestoneAccent ? (
                  <p className="text-[15px] leading-relaxed text-text-secondary">
                    Today&apos;s next milestone is{" "}
                    <span className="font-medium text-text-accent">{view.milestoneAccent}</span>
                    {view.milestoneRest ? (
                      <span> {view.milestoneRest}</span>
                    ) : null}
                    .
                  </p>
                ) : null}
              </header>

              <section
                aria-label="Next milestone"
                className="space-y-4 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-1 motion-safe:duration-500 motion-safe:delay-75"
              >
                <p className="text-[12px] font-medium uppercase tracking-[0.08em] text-text-tertiary">
                  {view.status}
                </p>

                <button
                  type="button"
                  onClick={() => navigate(view.href)}
                  className={cn(
                    "group relative w-full overflow-hidden rounded-2xl border border-primary/20",
                    "bg-[linear-gradient(180deg,color-mix(in_oklab,var(--primary)_7%,white)_0%,color-mix(in_oklab,var(--primary)_3%,white)_100%)]",
                    "px-5 py-6 text-left shadow-[0_1px_2px_rgba(15,23,42,0.04),0_8px_24px_-12px_rgba(15,110,106,0.28)]",
                    "transition-[transform,box-shadow,border-color] duration-200 ease-out",
                    "hover:-translate-y-0.5 hover:border-primary/35",
                    "hover:shadow-[0_2px_4px_rgba(15,23,42,0.05),0_16px_32px_-14px_rgba(15,110,106,0.35)]",
                    "active:translate-y-0 active:shadow-[0_1px_2px_rgba(15,23,42,0.04),0_8px_20px_-12px_rgba(15,110,106,0.22)]",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
                    "dark:bg-[linear-gradient(180deg,color-mix(in_oklab,var(--primary)_16%,transparent)_0%,color-mix(in_oklab,var(--primary)_6%,transparent)_100%)]",
                  )}
                >
                  <div
                    className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/35 to-transparent"
                    aria-hidden
                  />
                  <div className="relative flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-2">
                      <p className="text-[17px] font-semibold tracking-tight text-text-primary">
                        {view.recommendation}
                      </p>
                      <p className="text-[13px] leading-relaxed text-text-secondary">
                        {view.detail}
                      </p>
                      {view.context ? (
                        <p className="pt-0.5 text-[12px] tabular-nums text-text-secondary">
                          {view.context}
                        </p>
                      ) : null}
                    </div>
                    <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-text-accent transition-colors duration-200 group-hover:bg-primary/15">
                      <ArrowRight className="size-4 transition-transform duration-200 ease-out group-hover:translate-x-1" />
                    </span>
                  </div>
                </button>
              </section>

              <footer className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[12px] text-text-secondary motion-safe:animate-in motion-safe:fade-in motion-safe:duration-500 motion-safe:delay-150">
                {homeProject ? (
                  <button
                    type="button"
                    className="group inline-flex max-w-full items-center gap-1.5 font-medium text-text-accent transition-colors hover:opacity-90"
                    onClick={() => {
                      setCurrentProjectId(homeProject.id);
                      navigate(`/projects/${homeProject.id}`);
                    }}
                  >
                    <span className="truncate">Continue {homeProject.name}</span>
                    <ArrowRight
                      className="size-3 shrink-0 opacity-70 transition-transform duration-200 ease-out group-hover:translate-x-1 group-hover:opacity-100"
                      aria-hidden
                    />
                  </button>
                ) : (
                  <Link
                    to="/projects?new=1"
                    className="group inline-flex items-center gap-1.5 font-medium text-text-accent transition-colors hover:opacity-90"
                  >
                    Start a project
                    <ArrowRight
                      className="size-3 opacity-70 transition-transform duration-200 ease-out group-hover:translate-x-1 group-hover:opacity-100"
                      aria-hidden
                    />
                  </Link>
                )}
                <span className="text-border" aria-hidden>
                  ·
                </span>
                <Link to="/library" className="transition-colors hover:text-text-primary">
                  Library
                </Link>
                <span className="text-border" aria-hidden>
                  ·
                </span>
                <Link to="/projects" className="transition-colors hover:text-text-primary">
                  All projects
                </Link>
              </footer>
            </div>
          )}
        </div>
      </div>

      <div className="hidden lg:flex">
        <HomeAssistantPanel
          firstName={firstName}
          projectId={homeProjectId}
          projectTitle={projectTitle}
          papers={stateQ.data?.corpus?.papers ?? homeProject?.paper_count ?? 0}
          nextActionId={stateQ.data?.workflow?.nextAction?.id ?? null}
        />
      </div>
    </div>
  );
}
