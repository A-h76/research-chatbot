import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { chatApi } from "../api";
import type { Conversation, ConversationSummary } from "@/types/api";
import type { CreateConversationInput, UpdateConversationInput } from "../types";

export function useConversations() {
  return useQuery({ queryKey: queryKeys.conversations, queryFn: chatApi.list });
}

export function useConversation(id: number | null) {
  return useQuery({
    queryKey: id ? queryKeys.conversation(id) : ["conversations", "none"],
    queryFn: () => chatApi.get(id as number),
    enabled: id !== null,
  });
}

export function useCreateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateConversationInput) => chatApi.create(body),
    onSuccess: (conv) => {
      qc.invalidateQueries({ queryKey: queryKeys.conversations });
      qc.setQueryData(queryKeys.conversation(conv.id), { ...conv, messages: [] });
    },
  });
}

export function useUpdateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: UpdateConversationInput }) =>
      chatApi.update(id, body),
    onMutate: async ({ id, body }) => {
      await qc.cancelQueries({ queryKey: queryKeys.conversation(id) });
      const prevDetail = qc.getQueryData<Conversation>(queryKeys.conversation(id));
      const prevList = qc.getQueryData<ConversationSummary[]>(queryKeys.conversations);
      if (prevDetail) qc.setQueryData(queryKeys.conversation(id), { ...prevDetail, ...body });
      if (prevList)
        qc.setQueryData(
          queryKeys.conversations,
          prevList.map((c) => (c.id === id ? { ...c, ...body } : c))
        );
      return { prevDetail, prevList, id };
    },
    onError: (_err, _vars, ctx) => {
      if (!ctx) return;
      if (ctx.prevDetail) qc.setQueryData(queryKeys.conversation(ctx.id), ctx.prevDetail);
      if (ctx.prevList) qc.setQueryData(queryKeys.conversations, ctx.prevList);
    },
  });
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => chatApi.remove(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.conversations });
      qc.removeQueries({ queryKey: queryKeys.conversation(id) });
    },
  });
}
