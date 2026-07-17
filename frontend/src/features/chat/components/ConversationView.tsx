import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { MessageList, type LiveStream } from "./MessageList";
import { Composer } from "./Composer";
import { ChatTopControls } from "./ChatTopControls";
import { useConversation, useUpdateConversation } from "../hooks/useConversation";
import { useChatStream } from "../hooks/useChatStream";
import { useUI } from "@/context/UIContext";
import { chatOutbox } from "../lib/outbox";
import { appendUserMessage, removeLastAssistant } from "../lib/optimistic";
import type { ChatSettings, PendingFile, SendPayload } from "../types";
import type { Attachment, SearchMode } from "@/types/api";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";

export function ConversationView({ conversationId }: { conversationId: number }) {
  const qc = useQueryClient();
  const { data: conv, isLoading } = useConversation(conversationId);
  const updateConv = useUpdateConversation();
  const { defaultSearchMode } = useUI();
  const stream = useChatStream(conversationId);
  const [searchMode, setSearchMode] = useState<SearchMode>(defaultSearchMode);

  const messages = conv?.messages ?? [];

  const buildAndSend = (payload: SendPayload) => stream.send(payload);

  // Consume the first message queued by the welcome screen for this new chat.
  useEffect(() => {
    const item = chatOutbox.take(conversationId);
    if (item) {
      buildAndSend({
        conversation_id: conversationId,
        message: item.text,
        model: conv?.model ?? "",
        search: item.searchMode,
        attachments: item.attachmentIds,
      });
      setSearchMode(item.searchMode);
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
  };

  const onSettingsChange = (partial: Partial<ChatSettings>) => {
    if (partial.searchMode !== undefined) setSearchMode(partial.searchMode);
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
    });
  };

  const live: LiveStream | null =
    stream.isStreaming || stream.error
      ? {
          text: stream.streamingText,
          status: stream.status,
          sources: stream.sources,
          isStreaming: stream.isStreaming,
          error: stream.error,
        }
      : null;

  return (
    <div className="flex h-full flex-col">
      <ChatTopControls settings={settings} onSettingsChange={onSettingsChange} conversation={conv} />
      <div className="min-h-0 flex-1">
        <MessageList messages={messages} live={live} onRegenerate={onRegenerate} />
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
          Personal AI can make mistakes. Check important info.
        </p>
      </div>
    </div>
  );
}
