import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { memoriesApi } from "./api";
import type { Memory } from "@/types/api";

export function useMemories() {
  return useQuery({ queryKey: queryKeys.memories, queryFn: memoriesApi.list });
}

export function useUpdateMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: { fact?: string; importance?: number } }) =>
      memoriesApi.update(id, body),
    onSuccess: (updated) => {
      qc.setQueryData<Memory[]>(queryKeys.memories, (old) =>
        old?.map((m) => (m.id === updated.id ? updated : m))
      );
    },
  });
}

export function useDeleteMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => memoriesApi.remove(id),
    onSuccess: (_data, id) => {
      qc.setQueryData<Memory[]>(queryKeys.memories, (old) => old?.filter((m) => m.id !== id));
    },
  });
}
