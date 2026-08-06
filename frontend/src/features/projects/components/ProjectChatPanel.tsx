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
import type { ConversationSummary } from "@/types/api";

/** Default title for empty stubs that never received an auto-title. */
function isUntitledStub(c: ConversationSummary): boolean {
  const t = (c.title || "").trim().toLowerCase();
  return !t || t === "new chat" || t === "untitled" || t === "untitled chat";
}

/** Project-scoped chat list + new conversation. */
export function ProjectChatPanel({ projectId }: { projectId: number }) {
  const navigate = useNavigate();
  const { defaultModel } = useUI();
  const { data: me } = useMe();
  const { data: modelsData } = useModels();
  const { data: allConvos = [], isLoading } = useConversations();
  const createConvo = useCreateConversation();

  const projectConvos = useMemo(
    () =>
      allConvos.filter((c) => c.project_id === projectId && c.file_id == null),
    [allConvos, projectId],
  );

  /** Named chats only — hide empty "New chat" stubs from the list. */
  const namedConvos = useMemo(
    () => projectConvos.filter((c) => !isUntitledStub(c)).slice(0, 20),
    [projectConvos],
  );

  /** Most recent empty stub to reuse instead of creating duplicates. */
  const emptyStub = useMemo(
    () => projectConvos.find((c) => isUntitledStub(c)) ?? null,
    [projectConvos],
  );

  async function startChat() {
    if (emptyStub) {
      navigate(`/c/${emptyStub.id}`);
      return;
    }
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
            Retrieval is limited to papers in this project. Chats get a name after
            the first reply.
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

      {namedConvos.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border px-6 py-10 text-center space-y-3">
          <MessageSquare className="mx-auto size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No project conversations yet. Ask questions across your corpus — the
            chat will be named from your first exchange.
          </p>
          <Button variant="outline" size="sm" onClick={() => void startChat()}>
            Start chatting
          </Button>
        </div>
      ) : (
        <ul className="space-y-1">
          {namedConvos.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => navigate(`/c/${c.id}`)}
                className="flex w-full items-center gap-3 rounded-xl border border-border px-3 py-2.5 text-left transition-colors hover:bg-muted/50"
              >
                <MessageSquare className="size-4 shrink-0 text-primary" />
                <span className="min-w-0 flex-1 truncate text-sm font-medium">
                  {c.title}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
