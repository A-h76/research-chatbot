import { api } from "@/lib/apiClient";
import type { Conversation, ConversationSummary } from "@/types/api";
import type { CreateConversationInput, SendPayload, UpdateConversationInput } from "./types";

export const chatApi = {
  list: () => api.get<ConversationSummary[]>("/api/conversations"),
  get: (id: number) => api.get<Conversation>(`/api/conversations/${id}`),
  create: (body: CreateConversationInput) => api.post<Conversation>("/api/conversations", body),
  update: (id: number, body: UpdateConversationInput) =>
    api.patch<{ ok: boolean }>(`/api/conversations/${id}`, body),
  remove: (id: number) => api.delete<{ ok: boolean }>(`/api/conversations/${id}`),
  streamChat: (payload: SendPayload, signal: AbortSignal) =>
    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    }),
};
