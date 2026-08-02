import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Plus, AlertTriangle, RefreshCw } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ProjectCard } from "../components/ProjectCard";
import { ProjectDialog } from "../components/ProjectDialog";
import { ProjectsEmptyState } from "../components/ProjectsEmptyState";
import { useProjects } from "../useProjects";
import { useConversations } from "@/features/chat/hooks/useConversation";
import { useAllFiles } from "@/features/files/useFiles";
import { useMemories } from "@/features/memory/useMemories";
import type { Project } from "@/types/api";

export function ProjectsPage() {
  const { data: projects = [], isLoading, isError, refetch, isFetching } = useProjects();
  const { data: conversations = [] } = useConversations();
  const { data: files = [] } = useAllFiles();
  const { data: memories = [] } = useMemories();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);

  const libraryPapers = useMemo(
    () => files.filter((f) => f.kind === "document").slice(0, 6),
    [files],
  );

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // Pre-select library papers when the empty state first has them.
  useEffect(() => {
    if (projects.length > 0 || libraryPapers.length === 0) return;
    setSelectedIds((prev) => {
      if (prev.size > 0) return prev;
      return new Set(libraryPapers.map((p) => p.id));
    });
  }, [projects.length, libraryPapers]);

  // D8 — ⌘K “New project”
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

  const isEmpty = !isLoading && !isError && projects.length === 0;

  return (
    <PageContainer
      title="Research"
      description={
        isError
          ? "Couldn’t load your research projects."
          : isEmpty
            ? "Continue a literature review, synthesis, or writing effort."
            : "Pick up where you left off — papers, evidence, questions, and writing in one place."
      }
      actions={
        <Button
          variant={isEmpty || isError ? "outline" : "default"}
          onClick={openCreate}
          disabled={isError}
        >
          <Plus className="size-4" /> New research
        </Button>
      }
    >
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border p-5 space-y-3">
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-4/5" />
              <div className="flex gap-3 pt-2">
                <Skeleton className="h-3 w-12" />
                <Skeleton className="h-3 w-12" />
              </div>
            </div>
          ))}
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-border bg-muted/20 px-6 py-16 text-center">
          <AlertTriangle className="size-8 text-amber-600" />
          <p className="text-sm font-medium">Couldn’t load projects</p>
          <p className="max-w-sm text-[13px] text-muted-foreground">
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
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <ProjectCard
              key={p.id}
              project={p}
              chatCount={conversations.filter((c) => c.project_id === p.id).length}
              fileCount={files.filter((f) => f.project_id === p.id).length}
              memoryCount={memories.filter((m) => m.project_id === p.id).length}
              onOpen={() => navigate(`/projects/${p.id}`)}
              onEdit={() => {
                setEditing(p);
                setDialogOpen(true);
              }}
            />
          ))}
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
