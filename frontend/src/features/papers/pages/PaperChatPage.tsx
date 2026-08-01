import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft, BookOpen, ExternalLink,
  MessageSquare, Loader2, AlertCircle,
} from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { MessageList, type LiveStream } from "@/features/chat/components/MessageList";
import { Composer } from "@/features/chat/components/Composer";
import { PaperChatEvidenceRail } from "../components/PaperChatEvidenceRail";
import { useConversation, useCreateConversation } from "@/features/chat/hooks/useConversation";
import { useChatStream } from "@/features/chat/hooks/useChatStream";
import { useFile } from "@/features/files/useFiles";
import { useMe } from "@/features/profile/useMe";
import { useModels } from "@/features/models/useModels";
import { useUI } from "@/context/UIContext";
import { usePipeline, PipelineStatusPanel, isPipelineProcessing } from "@/features/pipeline";
import { chatOutbox } from "@/features/chat/lib/outbox";
import { appendUserMessage, removeLastAssistant } from "@/features/chat/lib/optimistic";
import { cn } from "@/lib/utils";
import { toast } from "@/components/common/Toast";
import type { ChatSettings, PendingFile } from "@/features/chat/types";
import type { Attachment } from "@/types/api";

// ── Paper header strip ────────────────────────────────────────────────────
function PaperHeader({ fileId }: { fileId: number }) {
  const { data: file } = useFile(fileId);
  const { derived } = usePipeline(fileId, { fileContentHash: null });
  const navigate = useNavigate();

  if (!file) return null;

  const title = file.title || file.name;
  const showPipeline =
    isPipelineProcessing(derived, file.meta_status) || derived.isError;

  return (
    <div className="border-b border-border bg-card/60 backdrop-blur-sm">
      <div className="flex items-center gap-3 px-4 py-2.5">
        <button
          type="button"
          onClick={() => navigate(`/papers/${fileId}`)}
          className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ChevronLeft className="size-4" />
          Overview
        </button>

        <Separator orientation="vertical" className="h-4" />

        <div className="flex min-w-0 flex-1 items-center gap-2.5">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium" title={title}>{title}</p>
            {(file.authors || file.year) && (
              <p className="truncate text-xs text-muted-foreground">
                {[file.authors?.split(";")[0]?.trim(), file.year].filter(Boolean).join(" · ")}
              </p>
            )}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {file.venue && (
            <Badge variant="outline" className="hidden text-xs sm:inline-flex">
              {file.venue.length > 20 ? file.venue.slice(0, 20) + "…" : file.venue}
            </Badge>
          )}
          {file.doi && (
            <a
              href={`https://doi.org/${file.doi}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground transition-colors hover:text-primary"
              title="Open DOI"
            >
              <ExternalLink className="size-3.5" />
            </a>
          )}
          <Badge
            className={cn(
              "text-xs",
              file.reading_status === "read"
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : file.reading_status === "reading"
                ? "bg-amber-50 text-amber-700 border-amber-200"
                : "bg-muted text-muted-foreground",
            )}
            variant="outline"
          >
            <BookOpen className="size-3" />
            {file.reading_status ?? "unread"}
          </Badge>
        </div>
      </div>
      {showPipeline && (
        <div className="px-4 pb-3">
          <PipelineStatusPanel
            derived={derived}
            metaStatus={file.meta_status}
            updatedAt={file.created_at}
            compact
          />
        </div>
      )}
    </div>
  );
}

// ── Paper-scoped empty state ──────────────────────────────────────────────
function PaperChatEmpty({ fileId }: { fileId: number }) {
  const { data: file } = useFile(fileId);
  const title = file?.title || file?.name || "this paper";

  const STARTERS = [
    "What is the main contribution of this paper?",
    "Explain the methodology in simple terms.",
    "What are the key limitations?",
    "Summarise the results section.",
  ];

  return (
    <div className="flex h-full flex-col items-center justify-center gap-5 px-6 text-center">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="space-y-2"
      >
        <div className="mx-auto flex size-10 items-center justify-center rounded-xl bg-accent-soft">
          <MessageSquare className="size-5 text-primary" />
        </div>
        <h2 className="text-[17px] font-semibold tracking-tight">Ask about this paper</h2>
        <p className="mx-auto max-w-md text-[13px] text-muted-foreground">
          Answers use only <span className="font-medium text-foreground/80">{title}</span>
          — with section and page citations when available.
        </p>
      </motion.div>

      <div className="grid w-full max-w-xl grid-cols-1 gap-2 sm:grid-cols-2">
        {STARTERS.map((s, i) => (
          <motion.div
            key={s}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04, duration: 0.2 }}
          >
            <button
              type="button"
              data-starter={s}
              className="w-full rounded-lg border border-border bg-card px-3 py-2.5 text-left text-[13px] text-muted-foreground transition-colors hover:border-primary/30 hover:bg-muted/40 hover:text-foreground"
            >
              {s}
            </button>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

// ── Main PaperChatPage ────────────────────────────────────────────────────
export function PaperChatPage() {
  const { fileId, conversationId: convIdParam } = useParams<{
    fileId: string;
    conversationId?: string;
  }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: me } = useMe();
  const { data: modelsData } = useModels();
  const { currentProjectId, defaultModel } = useUI();

  const fileIdNum = fileId ? Number(fileId) : null;
  const convIdNum = convIdParam ? Number(convIdParam) : null;

  // Conversation creation
  const createConversation = useCreateConversation();
  const [activeConvId, setActiveConvId] = useState<number | null>(convIdNum);

  // Once we have a file and no conversation yet, create one automatically
  const [creating, setCreating] = useState(false);
  const [createAttempt, setCreateAttempt] = useState(0);
  useEffect(() => {
    if (activeConvId || !fileIdNum || !me || creating) return;
    setCreating(true);
    const model = defaultModel || me.default_model || modelsData?.models[0] || "gpt-4o-mini";
    createConversation.mutateAsync({
      model,
      project_id: currentProjectId,
      file_id: fileIdNum,
    }).then((conv) => {
      setActiveConvId(conv.id);
      // Update the URL so the conversation is bookmarkable
      navigate(`/papers/${fileIdNum}/chat/${conv.id}`, { replace: true });
    }).catch(() => {
      toast.error("Could not start chat");
    }).finally(() => setCreating(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileIdNum, me, activeConvId, createAttempt]);

  // Settings (locked to paper-safe defaults — no web search)
  const [settings, setSettings] = useState<ChatSettings>({
    model: defaultModel || me?.default_model || "gpt-4o-mini",
    searchMode: "off",   // paper chat: no web search
    temperature: null,
    reasoningEffort: null,
    memoryEnabled: false, // paper chat doesn't use user memory
    skill: "ask",
  });

  const { data: conv, isLoading: convLoading } = useConversation(activeConvId);
  const stream = useChatStream(activeConvId ?? -1);

  // Consume outbox on route (handles the "Chat with this paper" button flow)
  useEffect(() => {
    if (!activeConvId) return;
    const item = chatOutbox.take(activeConvId);
    if (item) {
      stream.send({
        conversation_id: activeConvId,
        message: item.text,
        model: settings.model,
        search: "off",
        skill: item.skill ?? settings.skill,
        attachments: item.attachmentIds,
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConvId]);

  // Starter card click handler (bubbled up from the empty state)
  function handleStarterClick(e: React.MouseEvent) {
    const starter = (e.target as HTMLElement).closest("[data-starter]")?.getAttribute("data-starter");
    if (starter && activeConvId) {
      handleSend(starter, []);
    }
  }

  function handleSend(text: string, files: PendingFile[]) {
    if (!activeConvId) return;
    const attachments: Attachment[] = files.map((f) => ({
      id: f.id, name: f.name, kind: f.kind, mime: "",
    }));
    appendUserMessage(qc, activeConvId, text, attachments);
    stream.send({
      conversation_id: activeConvId,
      message: text,
      model: settings.model,
      search: "off",
      skill: settings.skill,
      attachments: files.map((f) => f.id),
    });
  }

  function handleRegenerate() {
    if (!activeConvId) return;
    removeLastAssistant(qc, activeConvId);
    stream.send({
      conversation_id: activeConvId,
      regenerate: true,
      model: settings.model,
      search: "off",
      skill: settings.skill,
    });
  }

  const messages = conv?.messages ?? [];
  const hasMessages = messages.length > 0;

  const live: LiveStream | null =
    stream.isStreaming || stream.error
      ? {
          text: stream.streamingText,
          status: stream.status,
          sources: stream.sources,
          references: stream.references,
          confidence: stream.confidence,
          warnings: stream.warnings,
          skill: stream.skill,
          isStreaming: stream.isStreaming,
          error: stream.error,
        }
      : null;

  // ── Render ──
  if (!fileIdNum) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Paper not found.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Paper context header */}
      {fileIdNum && <PaperHeader fileId={fileIdNum} />}

      {/* Chat area */}
      {creating || (convLoading && !conv) ? (
        <div className="flex flex-1 items-center justify-center gap-3 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
          <span className="text-sm">Opening paper chat…</span>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col" onClick={handleStarterClick}>
          {hasMessages || stream.isStreaming ? (
            <div className="grid min-h-0 flex-1 gap-0 lg:grid-cols-[minmax(0,1fr)_17rem]">
              <div className="min-h-0 min-w-0">
                <MessageList
                  messages={messages}
                  live={live}
                  onRegenerate={handleRegenerate}
                  fileId={fileIdNum}
                />
              </div>
              <aside className="hidden min-h-0 min-w-0 overflow-hidden border-l border-border p-3 lg:block">
                <PaperChatEvidenceRail fileId={fileIdNum} />
              </aside>
            </div>
          ) : (
            <div className="min-h-0 flex-1">
              <PaperChatEmpty fileId={fileIdNum} />
            </div>
          )}

          {/* Composer */}
          <div className="px-4 pb-4 pt-2">
            {activeConvId ? (
              <>
                <Composer
                  settings={settings}
                  onSettingsChange={(p) => setSettings((s) => ({ ...s, ...p }))}
                  onSend={handleSend}
                  streaming={stream.isStreaming}
                  onStop={stream.stop}
                  conversationId={activeConvId}
                  projectId={conv?.project_id ?? currentProjectId}
                  paperScoped
                />
                <p className="mt-2 text-center text-[11px] text-muted-foreground">
                  Answers are grounded in this paper only · web search is off
                </p>
              </>
            ) : (
              <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground py-3">
                <AlertCircle className="size-4" />
                Could not start chat.{" "}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setCreating(false);
                    setCreateAttempt((n) => n + 1);
                  }}
                >
                  Retry
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
