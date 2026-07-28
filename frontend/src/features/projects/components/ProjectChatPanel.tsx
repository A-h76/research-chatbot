import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { MessageSquare, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useConversations,
  useCreateConversation,
} from "@/features/chat/hooks/useConversation";
import { useModels } from "@/features/models/useModels";
import { useMe } from "@/features/profile/useMe";
import { useUI } from "@/context/UIContext";
import { toast } from "@/components/common/Toast";

/** Project-scoped chat list + new conversation. */
export function ProjectChatPanel({ projectId }: { projectId: number }) {
  const navigate = useNavigate();
  const { defaultModel } = useUI();
  const { data: me } = useMe();
  const { data: modelsData } = useModels();
  const { data: allConvos = [], isLoading } = useConversations();
  const createConvo = useCreateConversation();

  const convos = useMemo(
    () =>
      allConvos
        .filter((c) => c.project_id === projectId && c.file_id == null)
        .slice(0, 20),
    [allConvos, projectId],
  );

  async function startChat() {
    try {
      const model =
        defaultModel || me?.default_model || modelsData?.models[0] || "gpt-4o-mini";
      const conv = await createConvo.mutateAsync({
        model,
        project_id: projectId,
      });
      navigate(`/c/${conv.id}`);
    } catch {
      toast.error("Could not start chat");
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-10 w-32" />
        <Skeleton className="h-14 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">Project chat</h2>
          <p className="text-xs text-muted-foreground">
            Retrieval is limited to papers in this project.
          </p>
        </div>
        <Button
          size="sm"
          className="gap-1.5"
          disabled={createConvo.isPending}
          onClick={() => void startChat()}
        >
          <Plus className="size-3.5" /> New chat
        </Button>
      </div>

      {convos.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border px-6 py-10 text-center space-y-3">
          <MessageSquare className="mx-auto size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No project conversations yet. Ask questions across your corpus.
          </p>
          <Button variant="outline" size="sm" onClick={() => void startChat()}>
            Start chatting
          </Button>
        </div>
      ) : (
        <ul className="space-y-1">
          {convos.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => navigate(`/c/${c.id}`)}
                className="flex w-full items-center gap-3 rounded-xl border border-border px-3 py-2.5 text-left transition-colors hover:bg-muted/50"
              >
                <MessageSquare className="size-4 shrink-0 text-primary" />
                <span className="min-w-0 flex-1 truncate text-sm font-medium">
                  {c.title || "Untitled chat"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
