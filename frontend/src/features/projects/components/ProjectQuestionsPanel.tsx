import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Check,
  Circle,
  HelpCircle,
  MessageSquare,
  Pause,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { toast } from "@/components/common/Toast";
import {
  useCreateConversation,
} from "@/features/chat/hooks/useConversation";
import { useModels } from "@/features/models/useModels";
import { useMe } from "@/features/profile/useMe";
import { useUI } from "@/context/UIContext";
import { cn } from "@/lib/utils";
import type { ProjectQuestion, ProjectQuestionStatus } from "@/types/api";
import {
  useCreateQuestion,
  useDeleteQuestion,
  useProjectQuestions,
  useUpdateQuestion,
} from "../useProjects";
import { projectResearchUrl } from "../projectResearchNavigation";

const STATUS_META: Record<
  ProjectQuestionStatus,
  { label: string; icon: React.ReactNode; className: string }
> = {
  open: {
    label: "Open",
    icon: <Circle className="size-3.5" />,
    className: "text-amber-700 dark:text-amber-400",
  },
  answered: {
    label: "Answered",
    icon: <Check className="size-3.5" />,
    className: "text-emerald-700 dark:text-emerald-400",
  },
  parked: {
    label: "Parked",
    icon: <Pause className="size-3.5" />,
    className: "text-muted-foreground",
  },
};

function QuestionRow({
  question,
  onStatus,
  onDelete,
  onAnswerWithResearch,
  onAskInChat,
  busy,
}: {
  question: ProjectQuestion;
  onStatus: (status: ProjectQuestionStatus) => void;
  onDelete: () => void;
  onAnswerWithResearch: () => void;
  onAskInChat: () => void;
  busy: boolean;
}) {
  const meta = STATUS_META[question.status] ?? STATUS_META.open;
  return (
    <div className="rounded-xl border border-border px-3 py-3 space-y-2">
      <div className="flex items-start gap-2">
        <HelpCircle className={cn("mt-0.5 size-4 shrink-0", meta.className)} />
        <p className="min-w-0 flex-1 text-sm leading-relaxed">{question.text}</p>
      </div>
      <div className="flex flex-wrap items-center gap-1.5 pl-6">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-7 gap-1 text-[11px]"
          disabled={busy}
          onClick={onAnswerWithResearch}
        >
          <Sparkles className="size-3" />
          Answer with Research
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-7 gap-1 text-[11px]"
          disabled={busy}
          onClick={onAskInChat}
        >
          <MessageSquare className="size-3" />
          Ask in Chat
        </Button>
        {(["open", "answered", "parked"] as ProjectQuestionStatus[]).map((s) => (
          <button
            key={s}
            type="button"
            disabled={busy || question.status === s}
            onClick={() => onStatus(s)}
            className={cn(
              "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] transition-colors",
              question.status === s
                ? "bg-accent-soft font-medium text-foreground"
                : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
            )}
          >
            {STATUS_META[s].icon}
            {STATUS_META[s].label}
          </button>
        ))}
        <button
          type="button"
          disabled={busy}
          onClick={onDelete}
          className="ml-auto inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
          aria-label="Delete question"
        >
          <Trash2 className="size-3" />
          Delete
        </button>
      </div>
    </div>
  );
}

/** Lazy-loaded Questions tab — full list via GET …/questions, not hub fan-out. */
export function ProjectQuestionsPanel({ projectId }: { projectId: number }) {
  const navigate = useNavigate();
  const { defaultModel } = useUI();
  const { data: me } = useMe();
  const { data: modelsData } = useModels();
  const createConvo = useCreateConversation();
  const { data, isLoading } = useProjectQuestions(projectId, true);
  const createQ = useCreateQuestion(projectId);
  const updateQ = useUpdateQuestion(projectId);
  const deleteQ = useDeleteQuestion(projectId);
  const [draft, setDraft] = useState("");
  const [toDelete, setToDelete] = useState<ProjectQuestion | null>(null);

  const items = data?.items ?? [];
  const busy =
    createQ.isPending ||
    updateQ.isPending ||
    deleteQ.isPending ||
    createConvo.isPending;

  async function submit() {
    const text = draft.trim();
    if (!text) return;
    await createQ.mutateAsync({ text, source: "manual" });
    setDraft("");
  }

  function answerWithResearch(text: string) {
    navigate(projectResearchUrl(projectId, { query: text }));
  }

  async function askInChat(text: string) {
    try {
      const model =
        defaultModel || me?.default_model || modelsData?.models[0] || "gpt-4o-mini";
      const conv = await createConvo.mutateAsync({
        model,
        project_id: projectId,
      });
      navigate(`/c/${conv.id}`, { state: { draftMessage: text } });
    } catch {
      toast.error("Could not start chat");
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold">Research questions</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Track what you still need to answer. Notes stay freeform; questions are
          the research agenda.
        </p>
      </div>

      <div className="rounded-lg border border-border bg-muted/20 px-3 py-2.5 text-xs text-muted-foreground leading-relaxed">
        Dhund won&apos;t answer these automatically. Use{" "}
        <span className="font-medium text-foreground">Answer with Research</span> for
        cross-paper evidence from your papers, or{" "}
        <span className="font-medium text-foreground">Ask in Chat</span> for a
        conversational draft — then mark{" "}
        <span className="font-medium text-foreground">Answered</span> when you&apos;re
        satisfied.
      </div>

      <div className="flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit();
            }
          }}
          placeholder="What remains unanswered?"
          className="min-w-0 flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          disabled={busy}
        />
        <Button
          size="sm"
          className="gap-1.5 shrink-0"
          disabled={busy || !draft.trim()}
          onClick={() => void submit()}
        >
          <Plus className="size-3.5" /> Add
        </Button>
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border px-6 py-10 text-center space-y-2">
          <HelpCircle className="mx-auto size-8 text-muted-foreground" />
          <p className="text-sm font-medium">No questions yet</p>
          <p className="text-xs text-muted-foreground">
            Add the questions this project should answer, then use Research or Chat to
            investigate them.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((q) => (
            <QuestionRow
              key={q.id}
              question={q}
              busy={busy}
              onStatus={(status) =>
                updateQ.mutate({ questionId: q.id, body: { status } })
              }
              onDelete={() => setToDelete(q)}
              onAnswerWithResearch={() => answerWithResearch(q.text)}
              onAskInChat={() => void askInChat(q.text)}
            />
          ))}
        </div>
      )}

      <ConfirmDialog
        open={toDelete != null}
        onOpenChange={(open) => !open && setToDelete(null)}
        title="Delete research question?"
        entityName={toDelete?.text}
        description="This removes the question from the project agenda."
        confirmLabel="Delete question"
        cancelLabel="Keep"
        destructive
        onConfirm={async () => {
          if (!toDelete) return;
          await deleteQ.mutateAsync(toDelete.id);
          setToDelete(null);
        }}
      />
    </div>
  );
}
