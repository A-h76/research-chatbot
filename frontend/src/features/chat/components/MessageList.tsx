import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { UserMessage, AssistantMessage } from "./MessageBubble";
import { StatusLine } from "./StatusLine";
import type { Message, Source } from "@/types/api";

export interface LiveStream {
  text: string;
  status: string | null;
  sources: Source[];
  isStreaming: boolean;
  error: string | null;
}

export function MessageList({
  messages,
  live,
  onRegenerate,
}: {
  messages: Message[];
  live: LiveStream | null;
  onRegenerate: () => void;
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

  // The last assistant message can be regenerated (only when idle).
  const lastAssistantIdx = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return i;
    }
    return -1;
  })();

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
            {m.role === "user" ? (
              <UserMessage message={m} />
            ) : (
              <AssistantMessage
                content={m.content}
                sources={m.sources}
                onRegenerate={!live && i === lastAssistantIdx ? onRegenerate : undefined}
              />
            )}
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
                <AssistantMessage content={live.text} streaming={live.isStreaming} sources={live.sources} />
              )
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
