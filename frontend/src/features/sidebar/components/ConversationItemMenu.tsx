import { useState } from "react";
import { MoreHorizontal, Pencil, FolderInput, FolderMinus, Trash2, Download } from "lucide-react";
import { downloadExport, type ExportFormat } from "@/features/settings/api";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { useProjects } from "@/features/projects/useProjects";
import { useDeleteConversation, useUpdateConversation } from "@/features/chat/hooks/useConversation";
import { toast } from "@/components/common/Toast";
import type { ConversationSummary } from "@/types/api";

export function ConversationItemMenu({ convo }: { convo: ConversationSummary }) {
  const { data: projects = [] } = useProjects();
  const updateConvo = useUpdateConversation();
  const deleteConvo = useDeleteConversation();
  const [renaming, setRenaming] = useState(false);
  const [title, setTitle] = useState(convo.title);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const doRename = () => {
    const trimmed = title.trim();
    if (trimmed && trimmed !== convo.title) {
      updateConvo.mutate({ id: convo.id, body: { title: trimmed } });
    }
    setRenaming(false);
  };

  if (renaming) {
    return (
      <input
        autoFocus
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onBlur={doRename}
        onKeyDown={(e) => {
          if (e.key === "Enter") doRename();
          if (e.key === "Escape") setRenaming(false);
        }}
        onClick={(e) => e.stopPropagation()}
        className="w-full rounded-md border border-ring bg-background px-1.5 py-0.5 text-sm outline-none"
      />
    );
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          onClick={(e) => e.stopPropagation()}
          className="rounded-md p-1 text-muted-foreground opacity-0 hover:bg-sidebar-accent hover:text-foreground group-hover:opacity-100 data-[popup-open]:opacity-100"
        >
          <MoreHorizontal className="size-4" />
        </DropdownMenuTrigger>
        <DropdownMenuContent onClick={(e) => e.stopPropagation()}>
          <DropdownMenuItem onClick={() => setRenaming(true)}>
            <Pencil /> Rename
          </DropdownMenuItem>
          {projects.length > 0 && (
            <DropdownMenuSub>
              <DropdownMenuSubTrigger>
                <FolderInput /> Move to project
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                {projects.map((p) => (
                  <DropdownMenuItem
                    key={p.id}
                    onClick={() => updateConvo.mutate({ id: convo.id, body: { project_id: p.id } })}
                  >
                    {p.emoji} {p.name}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          )}
          {convo.project_id && (
            <DropdownMenuItem
              onClick={() => updateConvo.mutate({ id: convo.id, body: { project_id: null } })}
            >
              <FolderMinus /> Remove from project
            </DropdownMenuItem>
          )}
          <DropdownMenuSub>
            <DropdownMenuSubTrigger>
              <Download /> Export
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent>
              {(["pdf", "docx", "md", "txt", "json"] as ExportFormat[]).map((f) => (
                <DropdownMenuItem key={f} onClick={() => downloadExport(f, convo.id)}>
                  {f.toUpperCase()}
                </DropdownMenuItem>
              ))}
            </DropdownMenuSubContent>
          </DropdownMenuSub>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" onClick={() => setConfirmDelete(true)}>
            <Trash2 /> Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete this chat?"
        description="This can't be undone."
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          deleteConvo.mutate(convo.id);
          toast.success("Chat deleted");
        }}
      />
    </>
  );
}
