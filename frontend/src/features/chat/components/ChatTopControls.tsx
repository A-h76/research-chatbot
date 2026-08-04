import { useState } from "react";
import { MoreHorizontal, Trash2, FolderMinus, Route } from "lucide-react";
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
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useProjects } from "@/features/projects/useProjects";
import { useDeleteConversation, useUpdateConversation } from "../hooks/useConversation";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "@/components/common/Toast";
import { AiExecutionBeamInspector } from "@/features/research-flow";
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
    <div className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-4">
      {project && (
        <Link
          to={`/projects/${project.id}`}
          className="flex items-center gap-1.5 rounded-md border border-border bg-muted/40 px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <span>{project.emoji}</span>
          <span className="max-w-[14ch] truncate">{project.name}</span>
        </Link>
      )}
      <span className="min-w-0 truncate text-[13px] font-medium">{conversation.title}</span>
      <div className="ml-auto flex items-center gap-1">
        <Popover>
          <PopoverTrigger
            className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-hover hover:text-foreground"
            title="AI execution path"
          >
            <Route className="size-4" />
          </PopoverTrigger>
          <PopoverContent align="end" className="w-[min(92vw,28rem)] p-0">
            <AiExecutionBeamInspector
              compact
              execution={{
                research_job: conversation.file_id ? "analyze_paper" : "chat",
                capability: "scientific_reasoning",
                execution_policy: "balanced",
                provider: "openai",
                model: settings.model,
                prompt_version: "chat@live",
                router_version: "1.0",
              }}
            />
          </PopoverContent>
        </Popover>
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
        entityName={conversation.title || "Untitled chat"}
        description="Messages in this conversation will be permanently removed."
        confirmLabel="Delete chat"
        cancelLabel="Keep chat"
        destructive
        onConfirm={async () => {
          await deleteConv.mutateAsync(conversation.id);
          toast.success("Chat deleted");
          navigate("/");
        }}
      />
    </div>
  );
}
