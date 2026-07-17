import { useCallback, useReducer, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { iterateSSE } from "@/lib/sse";
import { chatApi } from "../api";
import type { Conversation, ConversationSummary, Message, Source } from "@/types/api";
import type { SendPayload } from "../types";

let optimisticAssistantId = -100000;

interface StreamState {
  streamingText: string;
  status: string | null;
  sources: Source[];
  isStreaming: boolean;
  error: string | null;
}

type Action =
  | { type: "RESET" }
  | { type: "DELTA"; text: string }
  | { type: "STATUS"; text: string }
  | { type: "DONE"; sources: Source[] }
  | { type: "ERROR"; text: string }
  | { type: "STOPPED" };

const initialState: StreamState = {
  streamingText: "",
  status: null,
  sources: [],
  isStreaming: false,
  error: null,
};

function reducer(state: StreamState, action: Action): StreamState {
  switch (action.type) {
    case "RESET":
      return { ...initialState, isStreaming: true };
    case "DELTA":
      return { ...state, streamingText: state.streamingText + action.text, status: null };
    case "STATUS":
      return { ...state, status: action.text };
    case "DONE":
      return { ...state, sources: action.sources, status: null, isStreaming: false };
    case "ERROR":
      return { ...state, error: action.text, status: null, isStreaming: false };
    case "STOPPED":
      return { ...state, status: null, isStreaming: false };
    default:
      return state;
  }
}

export function useChatStream(conversationId: number) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const abortRef = useRef<AbortController | null>(null);
  const qc = useQueryClient();

  const run = useCallback(
    async (payload: SendPayload) => {
      dispatch({ type: "RESET" });
      const controller = new AbortController();
      abortRef.current = controller;
      let full = "";
      let sources: Source[] = [];
      try {
        const res = await chatApi.streamChat(payload, controller.signal);
        if (!res.ok || !res.body) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.error || "Request failed");
        }
        for await (const { event, data } of iterateSSE(res.body)) {
          if (event === "delta") {
            full += data.text;
            dispatch({ type: "DELTA", text: data.text });
          } else if (event === "status") {
            dispatch({ type: "STATUS", text: data.text });
          } else if (event === "done") {
            sources = data.sources || [];
            if (data.title) {
              qc.setQueryData<Conversation>(queryKeys.conversation(conversationId), (old) =>
                old ? { ...old, title: data.title } : old
              );
              qc.setQueryData<ConversationSummary[]>(queryKeys.conversations, (old) =>
                old?.map((c) => (c.id === conversationId ? { ...c, title: data.title } : c))
              );
            }
            // Append the finished assistant turn to the cache so it replaces
            // the live bubble seamlessly (no flicker before the refetch lands).
            const assistantMsg: Message = {
              id: optimisticAssistantId--,
              role: "assistant",
              content: full,
              sources,
              attachments: [],
            };
            qc.setQueryData<Conversation>(queryKeys.conversation(conversationId), (old) =>
              old ? { ...old, messages: [...old.messages, assistantMsg] } : old
            );
            dispatch({ type: "DONE", sources });
          } else if (event === "error") {
            throw new Error(data.text);
          }
        }
        // Reconcile with the authoritative persisted messages (ids, sources,
        // attachments) — mirrors the old app's `loadConvos().then(renderConvos)`.
        qc.invalidateQueries({ queryKey: queryKeys.conversation(conversationId) });
        qc.invalidateQueries({ queryKey: queryKeys.conversations });
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          // Keep the partial text as a client-only bubble (the server does not
          // persist an aborted turn — it will vanish on next reload, matching
          // the previous app's behavior).
          if (full) {
            const partial: Message = {
              id: optimisticAssistantId--,
              role: "assistant",
              content: full + " *(stopped)*",
              sources,
              attachments: [],
            };
            qc.setQueryData<Conversation>(queryKeys.conversation(conversationId), (old) =>
              old ? { ...old, messages: [...old.messages, partial] } : old
            );
          }
          dispatch({ type: "STOPPED" });
        } else {
          dispatch({ type: "ERROR", text: err instanceof Error ? err.message : String(err) });
        }
      } finally {
        abortRef.current = null;
      }
    },
    [conversationId, qc]
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  return { ...state, send: run, regenerate: run, stop };
}
