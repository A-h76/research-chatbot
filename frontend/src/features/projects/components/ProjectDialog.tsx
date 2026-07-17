import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogFooter,
  DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input }    from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label }    from "@/components/ui/label";
import { Button }   from "@/components/ui/button";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { useCreateProject, useDeleteProject, useUpdateProject } from "../useProjects";
import { useUI } from "@/context/UIContext";
import { toast } from "@/components/common/Toast";
import type { Project } from "@/types/api";

export function ProjectDialog({
  open,
  onOpenChange,
  project,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project?: Project | null;
}) {
  const createProject = useCreateProject();
  const updateProject = useUpdateProject();
  const deleteProject = useDeleteProject();
  const { currentProjectId, setCurrentProjectId } = useUI();

  const [emoji,        setEmoji]        = useState("");
  const [name,         setName]         = useState("");
  const [description,  setDescription]  = useState("");
  const [instructions, setInstructions] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (open) {
      setEmoji(project?.emoji ?? "");
      setName(project?.name  ?? "");
      setDescription(project?.description  ?? "");
      setInstructions(project?.instructions ?? "");
    }
  }, [open, project]);

  const save = async () => {
    if (!name.trim()) {
      toast.error("Give the project a name");
      return;
    }
    const body = {
      name:         name.trim(),
      emoji:        emoji.trim() || "📁",
      description:  description.trim(),
      instructions: instructions.trim(),
    };
    if (project) {
      await updateProject.mutateAsync({ id: project.id, body });
      toast.success("Project updated");
    } else {
      await createProject.mutateAsync(body);
      toast.success("Project created");
    }
    onOpenChange(false);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{project ? "Edit research project" : "New research project"}</DialogTitle>
          </DialogHeader>

          <div className="grid gap-3">
            {/* Emoji + Name on one row */}
            <div className="flex gap-2">
              <div className="grid w-20 gap-1.5">
                <Label>Emoji</Label>
                <Input
                  value={emoji}
                  maxLength={4}
                  placeholder="📚"
                  onChange={(e) => setEmoji(e.target.value)}
                />
              </div>
              <div className="grid flex-1 gap-1.5">
                <Label>Project name</Label>
                <Input
                  value={name}
                  placeholder="My Thesis"
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
            </div>

            {/* Description */}
            <div className="grid gap-1.5">
              <Label>Description</Label>
              <Input
                value={description}
                placeholder="Brief description of what this project is about"
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            {/* Custom AI instructions */}
            <div className="grid gap-1.5">
              <Label>
                Custom AI instructions
                <span className="ml-1.5 text-[11px] font-normal text-muted-foreground">
                  — used in every chat in this project
                </span>
              </Label>
              <Textarea
                value={instructions}
                placeholder="e.g. My thesis topic is X. Always cite in APA. Assume familiarity with Y."
                onChange={(e) => setInstructions(e.target.value)}
                className="min-h-24"
              />
            </div>
          </div>

          <DialogFooter className="items-center">
            {project && (
              <Button
                variant="destructive"
                className="mr-auto"
                onClick={() => setConfirmDelete(true)}
              >
                Delete
              </Button>
            )}
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={save}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {project && (
        <ConfirmDialog
          open={confirmDelete}
          onOpenChange={setConfirmDelete}
          title="Delete this research project?"
          description="Chats and files are kept — they'll just be moved out of the project."
          confirmLabel="Delete project"
          destructive
          onConfirm={async () => {
            await deleteProject.mutateAsync(project.id);
            if (currentProjectId === project.id) setCurrentProjectId(null);
            toast.success("Project deleted");
            onOpenChange(false);
          }}
        />
      )}
    </>
  );
}
