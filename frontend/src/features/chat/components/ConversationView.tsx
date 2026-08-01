import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";
import { MessageList, type LiveStream } from "./MessageList";
import { Composer } from "./Composer";
import { ChatTopControls } from "./ChatTopControls";
import { ProjectInquiryRail } from "./ProjectInquiryRail";
import { useConversation, useUpdateConversation } from "../hooks/useConversation";
import { useChatStream } from "../hooks/useChatStream";
import { useUI } from "@/context/UIContext";
import { chatOutbox } from "../lib/outbox";
import { appendUserMessage, removeLastAssistant } from "../lib/optimistic";
import type { ChatSettings, PendingFile, SendPayload } from "../types";
import type { Attachment, SearchMode } from "@/types/api";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";

/** D6 T3 — demoted global / project inquiry conversation. */
export function ConversationView({ conversationId }: { conversationId: number }) {
  const qc = useQueryClient();
  const { data: conv, isLoading } = useConversation(conversationId);
  const updateConv = useUpdateConversation();
  const { defaultSearchMode } = useUI();
  const stream = useChatStream(conversationId);
  const [searchMode, setSearchMode] = useState<SearchMode>(defaultSearchMode);
  const [skill, setSkill] = useState<ChatSettings["skill"]>("ask");

  const messages = conv?.messages ?? [];
  const projectId = conv?.project_id ?? null;
  const fileId = conv?.file_id ?? null;

  const buildAndSend = (payload: SendPayload) => stream.send(payload);

  useEffect(() => {
    const item = chatOutbox.take(conversationId);
    if (item) {
      buildAndSend({
        conversation_id: conversationId,
        message: item.text,
        model: conv?.model ?? "",
        search: item.searchMode,
        skill: item.skill ?? "ask",
        attachments: item.attachmentIds,
      });
      setSearchMode(item.searchMode);
      if (item.skill) setSkill(item.skill);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  if (isLoading || !conv) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  const settings: ChatSettings = {
    model: conv.model,
    searchMode,
    temperature: conv.temperature,
    reasoningEffort: conv.reasoning_effort,
    memoryEnabled: conv.memory_enabled,
    skill,
  };

  const onSettingsChange = (partial: Partial<ChatSettings>) => {
    if (partial.searchMode !== undefined) setSearchMode(partial.searchMode);
    if (partial.skill !== undefined) setSkill(partial.skill);
    const body: Record<string, unknown> = {};
    if (partial.model !== undefined) body.model = partial.model;
    if (partial.temperature !== undefined) body.temperature = partial.temperature;
    if (partial.reasoningEffort !== undefined) body.reasoning_effort = partial.reasoningEffort;
    if (partial.memoryEnabled !== undefined) body.memory_enabled = partial.memoryEnabled;
    if (Object.keys(body).length) updateConv.mutate({ id: conversationId, body });
  };

  const onSend = (text: string, files: PendingFile[]) => {
    const attachments: Attachment[] = files.map((f) => ({
      id: f.id,
      name: f.name,
      kind: f.kind,
      mime: "",
    }));
    appendUserMessage(qc, conversationId, text, attachments);
    buildAndSend({
      conversation_id: conversationId,
      message: text,
      model: settings.model,
      search: searchMode,
      skill,
      attachments: files.map((f) => f.id),
    });
  };

  const onRegenerate = () => {
    removeLastAssistant(qc, conversationId);
    buildAndSend({
      conversation_id: conversationId,
      regenerate: true,
      model: settings.model,
      search: searchMode,
      skill,
    });
  };

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

  const showProjectRail = projectId != null && fileId == null;

  return (
    <div className="flex h-full min-h-0 flex-col">
      {fileId != null && (
        <div className="flex items-center gap-2 border-b border-border px-4 py-2 text-[13px]">
          <Link
            to={`/papers/${fileId}/chat/${conversationId}`}
            className="inline-flex items-center gap-1 text-primary hover:underline"
          >
            Open paper chat
          </Link>
          <span className="text-muted-foreground">· evidence rail and workspace refs</span>
        </div>
      )}
      {projectId != null && fileId == null && (
        <div className="flex items-center gap-2 border-b border-border px-4 py-2 text-[13px]">
          <Link
            to={`/projects/${projectId}`}
            className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="size-3.5" /> Project
          </Link>
          <span className="text-muted-foreground">· project-scoped inquiry</span>
        </div>
      )}
      <ChatTopControls settings={settings} onSettingsChange={onSettingsChange} conversation={conv} />
      <div
        className={
          showProjectRail
            ? "grid min-h-0 flex-1 gap-0 lg:grid-cols-[minmax(0,1fr)_17rem]"
            : "min-h-0 flex-1"
        }
      >
        <div className="min-h-0 min-w-0">
          <MessageList
            messages={messages}
            live={live}
            onRegenerate={onRegenerate}
            fileId={fileId ?? undefined}
          />
        </div>
        {showProjectRail && (
          <aside className="hidden min-h-0 min-w-0 overflow-hidden border-l border-border p-3 lg:block">
            <ProjectInquiryRail projectId={projectId} />
          </aside>
        )}
      </div>
      <div className="px-4 pb-4">
        <Composer
          settings={settings}
          onSettingsChange={onSettingsChange}
          onSend={onSend}
          streaming={stream.isStreaming}
          onStop={stream.stop}
          conversationId={conversationId}
          projectId={conv.project_id}
        />
        <p className="mt-2 text-center text-[11px] text-muted-foreground">
          {projectId
            ? "Project-scoped answers · pick a research skill · prefer Paper Chat for passage links"
            : "Pick a research skill · open a paper for passage-linked chat"}
        </p>
      </div>
    </div>
  );
}
