import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Plus, FolderKanban } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { ProjectCard } from "../components/ProjectCard";
import { ProjectDialog } from "../components/ProjectDialog";
import { useProjects } from "../useProjects";
import { useConversations } from "@/features/chat/hooks/useConversation";
import { useAllFiles } from "@/features/files/useFiles";
import { useMemories } from "@/features/memory/useMemories";
import type { Project } from "@/types/api";

export function ProjectsPage() {
  const { data: projects = [] }      = useProjects();
  const { data: conversations = [] } = useConversations();
  const { data: files = [] }         = useAllFiles();
  const { data: memories = [] }      = useMemories();
  const navigate                     = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [dialogOpen,  setDialogOpen]  = useState(false);
  const [editing,     setEditing]     = useState<Project | null>(null);

  // D8 — ⌘K “New project”
  useEffect(() => {
    if (searchParams.get("new") !== "1") return;
    setEditing(null);
    setDialogOpen(true);
    const next = new URLSearchParams(searchParams);
    next.delete("new");
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  return (
    <PageContainer
      title="Projects"
      description="Your research home — open a project to collect papers, track questions, and work with evidence."
      actions={
        <Button
          onClick={() => { setEditing(null); setDialogOpen(true); }}
        >
          <Plus className="size-4" /> New project
        </Button>
      }
    >
      {projects.length === 0 ? (
        <EmptyState
          icon={<FolderKanban className="size-8" />}
          title="Start your first research project"
          description="Dhund is organised around projects, not individual PDFs. Create one to keep papers, questions, and insights together."
          action={
            <Button onClick={() => { setEditing(null); setDialogOpen(true); }}>
              <Plus className="size-4" /> Create first project
            </Button>
          }
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
              onEdit={() => { setEditing(p); setDialogOpen(true); }}
            />
          ))}
        </div>
      )}
      <ProjectDialog open={dialogOpen} onOpenChange={setDialogOpen} project={editing} />
    </PageContainer>
  );
}
