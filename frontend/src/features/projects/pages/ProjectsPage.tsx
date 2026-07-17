import { useState } from "react";
import { useNavigate } from "react-router-dom";
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
  const [dialogOpen,  setDialogOpen]  = useState(false);
  const [editing,     setEditing]     = useState<Project | null>(null);

  return (
    <PageContainer
      title="Research Projects"
      description="Each project has its own knowledge context — papers, chats, and memory stay isolated."
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
          title="No projects yet"
          description="Create a project to keep related papers, chats, and instructions together — with its own isolated AI context."
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
