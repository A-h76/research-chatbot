import { useCallback, useEffect, useMemo, useRef, useState, memo } from "react";
import { motion } from "framer-motion";
import { ArrowDown } from "lucide-react";
import { UserMessage, AssistantMessage } from "./MessageBubble";
import { StatusLine } from "./StatusLine";
import type { Message, Source } from "@/types/api";
import { mapExplainableChat } from "@/features/papers/mappers/chat";
import type { WorkspaceReference } from "@/features/papers/mappers/chat";
import { QuotaNotice } from "@/features/settings/components/QuotaNotice";
import type { QuotaPayload } from "@/features/settings/quotaMessaging";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface LiveStream {
  text: string;
  status: string | null;
  sources: Source[];
  references?: Message["references"];
  confidence?: number;
  warnings?: string[];
  skill?: string;
  isStreaming: boolean;
  error: string | null;
  quota?: QuotaPayload | null;
}

const MemoUserMessage = memo(UserMessage);
const MemoAssistantMessage = memo(AssistantMessage);

const NEAR_BOTTOM_PX = 120;

type ExplainableSlice = {
  answer: string;
  reasoning?: string;
  confidence?: number;
  warnings?: string[];
  references?: WorkspaceReference[];
  skill?: string;
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
      skill={explainable?.skill ?? message.skill}
      onRegenerate={onRegenerate}
    />
  );
}

const MemoHistoricalRow = memo(HistoricalRow);

function isNearBottom(el: HTMLElement): boolean {
  return el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
}

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
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);
  const [showJump, setShowJump] = useState(false);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "auto") => {
    const el = scrollRef.current;
    if (!el) return;
    // Prefer scrollTop on this container only — never scrollIntoView (page jump).
    if (behavior === "smooth") {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    } else {
      el.scrollTop = el.scrollHeight;
    }
  }, []);

  const jumpToLatest = useCallback(() => {
    stickToBottomRef.current = true;
    setShowJump(false);
    scrollToBottom("smooth");
  }, [scrollToBottom]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      const near = isNearBottom(el);
      stickToBottomRef.current = near;
      setShowJump(!near);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  // New messages: always follow user sends; otherwise respect stick-to-bottom.
  const messageCount = messages.length;
  const lastRole = messages[messageCount - 1]?.role;
  useEffect(() => {
    if (lastRole === "user") {
      stickToBottomRef.current = true;
      setShowJump(false);
      scrollToBottom("auto");
      return;
    }
    if (stickToBottomRef.current) {
      scrollToBottom("auto");
    } else if (messageCount > 0) {
      setShowJump(true);
    }
  }, [messageCount, lastRole, scrollToBottom]);

  // Streaming: follow only when user is near bottom; no forced yank.
  useEffect(() => {
    if (!(live?.isStreaming || live?.status || live?.text)) return;
    if (stickToBottomRef.current) {
      scrollToBottom("auto");
    }
  }, [live?.text, live?.status, live?.isStreaming, scrollToBottom]);

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
            skill:
              m.skill ||
              (typeof view.metadata.skill === "string" ? view.metadata.skill : undefined),
          });
        }
      }
    }
    return map;
  }, [messages, fileId]);

  return (
    <div className="relative h-full min-h-0">
      <div
        ref={scrollRef}
        className="scrollbar-thin h-full min-h-0 overflow-y-auto overscroll-contain"
        role="log"
        aria-live="polite"
      >
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
                live.quota ? (
                  <QuotaNotice quota={live.quota} tone="error" />
                ) : (
                  <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    {live.error}
                  </div>
                )
              ) : (
                (live.text || live.isStreaming) && (
                  <AssistantMessage
                    content={live.text}
                    streaming={live.isStreaming}
                    sources={live.sources}
                    confidence={!live.isStreaming ? live.confidence : undefined}
                    warnings={!live.isStreaming ? live.warnings : undefined}
                    skill={!live.isStreaming ? live.skill : undefined}
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
          <div aria-hidden className="h-px w-full shrink-0" />
        </div>
      </div>

      <div
        className={cn(
          "pointer-events-none absolute inset-x-0 bottom-3 z-10 flex justify-center transition-opacity",
          showJump ? "opacity-100" : "opacity-0",
        )}
      >
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={!showJump}
          onClick={jumpToLatest}
          className={cn(
            "pointer-events-auto gap-1.5 rounded-full border border-border bg-background/95 shadow-md backdrop-blur",
            !showJump && "invisible",
          )}
        >
          <ArrowDown className="size-3.5" />
          Jump to latest
        </Button>
      </div>
    </div>
  );
}
