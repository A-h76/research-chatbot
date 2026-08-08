/**
 * Projects — Constitution: one question.
 * "Which research should I advance?"
 * Continue vs Other · thin stage/next · no mystery metrics.
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQueries } from "@tanstack/react-query";
import { Plus, AlertTriangle, RefreshCw } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useUI } from "@/context/UIContext";
import { assistantApi } from "@/features/assistant/api";
import { useAllFiles } from "@/features/files/useFiles";
import type { Project } from "@/types/api";
import { ProjectCard } from "../components/ProjectCard";
import { ProjectDialog } from "../components/ProjectDialog";
import { ProjectsEmptyState } from "../components/ProjectsEmptyState";
import { buildProjectsListView } from "../projectsListViewModel";
import { useProjects } from "../useProjects";

export function ProjectsPage() {
  const { data: projects = [], isLoading, isError, refetch, isFetching } = useProjects();
  const { data: files = [] } = useAllFiles();
  const { currentProjectId, setCurrentProjectId } = useUI();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);

  const libraryPapers = useMemo(
    () => files.filter((f) => f.kind === "document").slice(0, 6),
    [files],
  );

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (projects.length > 0 || libraryPapers.length === 0) return;
    setSelectedIds((prev) => {
      if (prev.size > 0) return prev;
      return new Set(libraryPapers.map((p) => p.id));
    });
  }, [projects.length, libraryPapers]);

  useEffect(() => {
    if (searchParams.get("new") !== "1") return;
    setEditing(null);
    setDialogOpen(true);
    const next = new URLSearchParams(searchParams);
    next.delete("new");
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  const openCreate = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const fileCounts = useMemo(() => {
    const m = new Map<number, number>();
    for (const f of files) {
      if (f.kind !== "document" || f.project_id == null) continue;
      m.set(f.project_id, (m.get(f.project_id) ?? 0) + 1);
    }
    return m;
  }, [files]);

  const stateQueries = useQueries({
    queries: projects.map((p) => ({
      queryKey: ["assistant", "research-state", "projects-list", p.id],
      queryFn: () => assistantApi.researchState(p.id),
      staleTime: 60_000,
      enabled: projects.length > 0,
    })),
  });

  const statesById = useMemo(() => {
    const m = new Map<number, (typeof stateQueries)[number]["data"]>();
    projects.forEach((p, i) => {
      m.set(p.id, stateQueries[i]?.data);
    });
    return m;
  }, [projects, stateQueries]);

  const view = useMemo(
    () =>
      buildProjectsListView({
        projects,
        currentProjectId,
        statesById,
        fileCounts,
      }),
    [projects, currentProjectId, statesById, fileCounts],
  );

  const isEmpty = !isLoading && !isError && projects.length === 0;

  function openProject(project: Project, href: string) {
    setCurrentProjectId(project.id);
    navigate(href.startsWith("/") ? href : `/projects/${project.id}`);
  }

  return (
    <PageContainer
      title="Research Projects"
      description={
        isError
          ? "Couldn’t load your research projects."
          : isEmpty
            ? "Start a literature review, synthesis, or writing effort."
            : "Continue your active research or start a new one."
      }
      actions={
        <Button
          variant="outline"
          size="sm"
          onClick={openCreate}
          disabled={isError}
          className="text-text-secondary hover:text-text-primary"
        >
          <Plus className="size-3.5" /> New research
        </Button>
      }
    >
      {isLoading ? (
        <div className="max-w-3xl space-y-4" aria-busy="true" data-density="high">
          <Skeleton className="h-28 w-full rounded-2xl" />
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-start gap-3 py-3">
              <Skeleton className="size-9 rounded-md" />
              <div className="min-w-0 flex-1 space-y-2">
                <Skeleton className="h-3.5 w-2/5" />
                <Skeleton className="h-3 w-3/5" />
              </div>
            </div>
          ))}
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-md border border-border bg-muted/20 px-6 py-16 text-center">
          <AlertTriangle className="size-8 text-sem-warn" />
          <p className="text-sm font-medium text-text-primary">Couldn’t load projects</p>
          <p className="max-w-sm text-[13px] text-text-secondary">
            Check your connection and try again. This is not an empty library —
            your research may still be on the server.
          </p>
          <Button
            variant="outline"
            size="sm"
            disabled={isFetching}
            onClick={() => void refetch()}
          >
            <RefreshCw className={`size-3.5 ${isFetching ? "animate-spin" : ""}`} />
            Retry
          </Button>
        </div>
      ) : isEmpty ? (
        <ProjectsEmptyState
          papers={libraryPapers}
          selectedIds={selectedIds}
          onToggle={(id) => {
            setSelectedIds((prev) => {
              const next = new Set(prev);
              if (next.has(id)) next.delete(id);
              else next.add(id);
              return next;
            });
          }}
          onCreate={openCreate}
        />
      ) : (
        <div className="mx-auto max-w-3xl space-y-8" data-density="high">
          {view.continueRow ? (
            <section aria-label="Continue research" className="space-y-3">
              <p className="text-[12px] font-medium uppercase tracking-[0.08em] text-text-tertiary">
                Continue
              </p>
              <ProjectCard
                row={view.continueRow}
                featured
                onOpen={() =>
                  openProject(view.continueRow!.project, view.continueRow!.href)
                }
                onEdit={() => {
                  setEditing(view.continueRow!.project);
                  setDialogOpen(true);
                }}
              />
            </section>
          ) : null}

          {view.otherRows.length > 0 ? (
            <section aria-label="Other projects" className="space-y-1">
              <p className="mb-2 text-[12px] font-medium uppercase tracking-[0.08em] text-text-tertiary">
                Other projects
              </p>
              <div>
                {view.otherRows.map((row) => (
                  <ProjectCard
                    key={row.project.id}
                    row={row}
                    onOpen={() => openProject(row.project, `/projects/${row.project.id}`)}
                    onEdit={() => {
                      setEditing(row.project);
                      setDialogOpen(true);
                    }}
                  />
                ))}
              </div>
            </section>
          ) : null}

          <div className="pt-1">
            <button
              type="button"
              onClick={openCreate}
              className="inline-flex items-center gap-1.5 text-[12px] font-medium text-text-secondary transition-colors hover:text-text-accent"
            >
              <Plus className="size-3.5" />
              New research
            </button>
          </div>
        </div>
      )}
      <ProjectDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        project={editing}
        fileIdsToAttach={editing ? undefined : Array.from(selectedIds)}
      />
    </PageContainer>
  );
}
