import type { QueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import type { Attachment, Conversation, Message } from "@/types/api";

let optimisticIdCounter = -1;

export function appendUserMessage(
  qc: QueryClient,
  id: number,
  content: string,
  attachments: Attachment[]
) {
  const msg: Message = {
    id: optimisticIdCounter--,
    role: "user",
    content: content || "(see attached files)",
    sources: [],
    attachments,
  };
  qc.setQueryData<Conversation>(queryKeys.conversation(id), (old) =>
    old ? { ...old, messages: [...old.messages, msg] } : old
  );
}

export function removeLastAssistant(qc: QueryClient, id: number) {
  qc.setQueryData<Conversation>(queryKeys.conversation(id), (old) => {
    if (!old) return old;
    const messages = [...old.messages];
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") {
        messages.splice(i, 1);
        break;
      }
    }
    return { ...old, messages };
  });
}
