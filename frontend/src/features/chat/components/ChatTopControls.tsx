import { useState } from "react";
import { MoreHorizontal, Trash2, FolderMinus } from "lucide-react";
import { ShareChatButton } from "./ShareChatButton";
import { ModelPickerPopover } from "./ModelPickerPopover";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { useProjects } from "@/features/projects/useProjects";
import { useDeleteConversation, useUpdateConversation } from "../hooks/useConversation";
import { useNavigate } from "react-router-dom";
import { toast } from "@/components/common/Toast";
import type { ChatSettings } from "../types";
import type { Conversation } from "@/types/api";

export function ChatTopControls({
  settings,
  onSettingsChange,
  conversation,
}: {
  settings: ChatSettings;
  onSettingsChange: (partial: Partial<ChatSettings>) => void;
  conversation: Conversation;
}) {
  const { data: projects = [] } = useProjects();
  const project = projects.find((p) => p.id === conversation.project_id);
  const deleteConv = useDeleteConversation();
  const updateConv = useUpdateConversation();
  const navigate = useNavigate();
  const [confirmDelete, setConfirmDelete] = useState(false);

  return (
    <div className="flex h-12 items-center gap-2 border-b border-border px-4">
      {project && (
        <span className="flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">
          <span>{project.emoji}</span>
          {project.name}
        </span>
      )}
      <span className="min-w-0 truncate text-sm font-medium">{conversation.title}</span>
      <div className="ml-auto flex items-center gap-1">
        <ModelPickerPopover value={settings.model} onChange={(m) => onSettingsChange({ model: m })} compact />
        <ShareChatButton />
        <DropdownMenu>
          <DropdownMenuTrigger
            render={<Button variant="ghost" size="icon" />}
            title="More"
          >
            <MoreHorizontal className="size-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {conversation.project_id && (
              <DropdownMenuItem
                onClick={() => updateConv.mutate({ id: conversation.id, body: { project_id: null } })}
              >
                <FolderMinus /> Remove from project
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onClick={() => setConfirmDelete(true)}>
              <Trash2 /> Delete chat
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete this chat?"
        description="This can't be undone."
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          deleteConv.mutate(conversation.id);
          toast.success("Chat deleted");
          navigate("/");
        }}
      />
    </div>
  );
}
