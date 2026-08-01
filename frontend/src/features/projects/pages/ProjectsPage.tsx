import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Plus } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/button";
import { ProjectCard } from "../components/ProjectCard";
import { ProjectDialog } from "../components/ProjectDialog";
import { ProjectsEmptyState } from "../components/ProjectsEmptyState";
import { useProjects } from "../useProjects";
import { useConversations } from "@/features/chat/hooks/useConversation";
import { useAllFiles } from "@/features/files/useFiles";
import { useMemories } from "@/features/memory/useMemories";
import type { Project } from "@/types/api";

export function ProjectsPage() {
  const { data: projects = [] } = useProjects();
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

  const isEmpty = projects.length === 0;

  return (
    <PageContainer
      title="Research"
      description={
        isEmpty
          ? "Continue a literature review, synthesis, or writing effort."
          : "Pick up where you left off — papers, evidence, questions, and writing in one place."
      }
      actions={
        <Button
          variant={isEmpty ? "outline" : "default"}
          onClick={openCreate}
        >
          <Plus className="size-4" /> New research
        </Button>
      }
    >
      {isEmpty ? (
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
