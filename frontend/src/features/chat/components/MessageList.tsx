import { useEffect, useMemo, useRef, memo } from "react";
import { motion } from "framer-motion";
import { UserMessage, AssistantMessage } from "./MessageBubble";
import { StatusLine } from "./StatusLine";
import type { Message, Source } from "@/types/api";
import { mapExplainableChat } from "@/features/papers/mappers/chat";
import type { WorkspaceReference } from "@/features/papers/mappers/chat";

export interface LiveStream {
  text: string;
  status: string | null;
  sources: Source[];
  references?: Message["references"];
  confidence?: number;
  warnings?: string[];
  isStreaming: boolean;
  error: string | null;
}

const MemoUserMessage = memo(UserMessage);
const MemoAssistantMessage = memo(AssistantMessage);

type ExplainableSlice = {
  answer: string;
  reasoning?: string;
  confidence?: number;
  warnings?: string[];
  references?: WorkspaceReference[];
};

function HistoricalRow({
  message,
  explainable,
  onRegenerate,
}: {
  message: Message;
  explainable: ExplainableSlice | null | undefined;
  onRegenerate?: () => void;
}) {
  if (message.role === "user") {
    return <MemoUserMessage message={message} />;
  }
  return (
    <MemoAssistantMessage
      content={explainable?.answer ?? message.content}
      sources={message.sources}
      reasoning={explainable?.reasoning}
      confidence={explainable?.confidence}
      warnings={explainable?.warnings}
      references={explainable?.references}
      onRegenerate={onRegenerate}
    />
  );
}

const MemoHistoricalRow = memo(HistoricalRow);

export function MessageList({
  messages,
  live,
  onRegenerate,
  fileId,
}: {
  messages: Message[];
  live: LiveStream | null;
  onRegenerate: () => void;
  /** When set, assistant turns are normalized via mapExplainableChat. */
  fileId?: number;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "auto" });
  }, [messages.length]);

  useEffect(() => {
    if (live?.isStreaming || live?.status) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [live?.text, live?.status, live?.isStreaming]);

  const lastAssistantIdx = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return i;
    }
    return -1;
  })();

  const explainableById = useMemo(() => {
    const map = new Map<number, ExplainableSlice>();
    for (const m of messages) {
      if (m.role === "assistant") {
        const view = mapExplainableChat(m, fileId != null ? { fileId } : undefined);
        if (view) {
          map.set(m.id, {
            answer: view.answer,
            reasoning: view.reasoning,
            confidence: view.confidence,
            warnings: view.warnings.length ? view.warnings : undefined,
            references: view.references.length ? view.references : undefined,
          });
        }
      }
    }
    return map;
  }, [messages, fileId]);

  return (
    <div ref={scrollRef} className="scrollbar-thin h-full overflow-y-auto" role="log" aria-live="polite">
      <span className="sr-only" aria-live="polite">
        {live?.status ?? (live?.isStreaming ? "Assistant is responding" : "")}
      </span>
      <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-6">
        {messages.map((m, i) => (
          <motion.div
            key={m.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
          >
            <MemoHistoricalRow
              message={m}
              explainable={explainableById.get(m.id)}
              onRegenerate={!live && i === lastAssistantIdx ? onRegenerate : undefined}
            />
          </motion.div>
        ))}

        {live && (live.isStreaming || live.text || live.status || live.error) && (
          <div>
            {live.status && <StatusLine text={live.status} />}
            {live.error ? (
              <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                ⚠ {live.error}
              </div>
            ) : (
              (live.text || live.isStreaming) && (
                <AssistantMessage
                  content={live.text}
                  streaming={live.isStreaming}
                  sources={live.sources}
                  confidence={!live.isStreaming ? live.confidence : undefined}
                  warnings={!live.isStreaming ? live.warnings : undefined}
                  references={
                    !live.isStreaming && live.references?.length
                      ? (mapExplainableChat(
                          {
                            role: "assistant",
                            content: live.text,
                            references: live.references,
                          },
                          fileId != null ? { fileId } : undefined,
                        )?.references ?? undefined)
                      : undefined
                  }
                />
              )
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
