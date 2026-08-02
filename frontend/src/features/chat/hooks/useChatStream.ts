import { useCallback, useReducer, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { iterateSSE } from "@/lib/sse";
import { ApiError } from "@/lib/apiClient";
import { formatApiFailure, quotaFromUnknown } from "@/lib/apiErrors";
import type { QuotaPayload } from "@/features/settings/quotaMessaging";
import { chatApi } from "../api";
import type { Conversation, ConversationSummary, Message, Source } from "@/types/api";
import type { SendPayload } from "../types";

let optimisticAssistantId = -100000;

interface StreamState {
  streamingText: string;
  status: string | null;
  sources: Source[];
  references: Message["references"];
  scope: Message["scope"];
  confidence: number | undefined;
  warnings: string[] | undefined;
  skill: string | undefined;
  isStreaming: boolean;
  error: string | null;
  quota: QuotaPayload | null;
}

type Action =
  | { type: "RESET" }
  | { type: "DELTA"; text: string }
  | { type: "STATUS"; text: string }
  | {
      type: "DONE";
      sources: Source[];
      references?: Message["references"];
      scope?: Message["scope"];
      confidence?: number;
      warnings?: string[];
      skill?: string;
    }
  | { type: "ERROR"; text: string; quota?: QuotaPayload | null }
  | { type: "STOPPED" };

const initialState: StreamState = {
  streamingText: "",
  status: null,
  sources: [],
  references: undefined,
  scope: undefined,
  confidence: undefined,
  warnings: undefined,
  skill: undefined,
  isStreaming: false,
  error: null,
  quota: null,
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
      return {
        ...state,
        sources: action.sources,
        references: action.references,
        scope: action.scope,
        confidence: action.confidence,
        warnings: action.warnings,
        skill: action.skill,
        status: null,
        isStreaming: false,
        quota: null,
      };
    case "ERROR":
      return {
        ...state,
        error: action.text,
        quota: action.quota ?? null,
        status: null,
        isStreaming: false,
      };
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
      let references: Message["references"];
      let scope: Message["scope"];
      let confidence: number | undefined;
      let warnings: string[] | undefined;
      let skill: string | undefined;
      try {
        const res = await chatApi.streamChat(payload, controller.signal);
        if (!res.ok || !res.body) {
          const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
          const code = typeof body.error === "string" ? body.error : undefined;
          throw new ApiError(String(body.detail || body.error || "Request failed"), res.status, {
            code,
            body,
            quota: quotaFromUnknown(body),
          });
        }
        for await (const { event, data } of iterateSSE(res.body)) {
          if (event === "delta") {
            full += data.text;
            dispatch({ type: "DELTA", text: data.text });
          } else if (event === "status") {
            dispatch({ type: "STATUS", text: data.text });
          } else if (event === "done") {
            sources = data.sources || [];
            references = Array.isArray(data.references) ? data.references : undefined;
            scope = data.scope && typeof data.scope === "object" ? data.scope : undefined;
            confidence =
              typeof data.confidence === "number" && Number.isFinite(data.confidence)
                ? data.confidence
                : undefined;
            warnings = Array.isArray(data.warnings)
              ? data.warnings.map(String).filter(Boolean)
              : undefined;
            skill = typeof data.skill === "string" ? data.skill : undefined;
            if (data.title) {
              qc.setQueryData<Conversation>(queryKeys.conversation(conversationId), (old) =>
                old ? { ...old, title: data.title } : old,
              );
              qc.setQueryData<ConversationSummary[]>(queryKeys.conversations, (old) =>
                old?.map((c) => (c.id === conversationId ? { ...c, title: data.title } : c)),
              );
            }
            const assistantMsg: Message = {
              id: optimisticAssistantId--,
              role: "assistant",
              content: full,
              sources,
              references,
              scope,
              confidence,
              warnings,
              skill,
              attachments: [],
            };
            qc.setQueryData<Conversation>(queryKeys.conversation(conversationId), (old) =>
              old ? { ...old, messages: [...old.messages, assistantMsg] } : old,
            );
            dispatch({
              type: "DONE",
              sources,
              references,
              scope,
              confidence,
              warnings,
              skill,
            });
          } else if (event === "error") {
            const quota = quotaFromUnknown(data);
            throw new ApiError(String(data.text || data.error || "Stream error"), 500, {
              code: typeof data.error === "string" ? data.error : undefined,
              body: data && typeof data === "object" ? (data as Record<string, unknown>) : undefined,
              quota,
            });
          }
        }
        qc.invalidateQueries({ queryKey: queryKeys.conversation(conversationId) });
        qc.invalidateQueries({ queryKey: queryKeys.conversations });
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          if (full) {
            const partial: Message = {
              id: optimisticAssistantId--,
              role: "assistant",
              content: full + " *(stopped)*",
              sources,
              attachments: [],
            };
            qc.setQueryData<Conversation>(queryKeys.conversation(conversationId), (old) =>
              old ? { ...old, messages: [...old.messages, partial] } : old,
            );
          }
          dispatch({ type: "STOPPED" });
        } else {
          dispatch({
            type: "ERROR",
            text: formatApiFailure(err, "Chat failed"),
            quota: quotaFromUnknown(err),
          });
        }
      } finally {
        abortRef.current = null;
      }
    },
    [conversationId, qc],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  return { ...state, send: run, regenerate: run, stop };
}
