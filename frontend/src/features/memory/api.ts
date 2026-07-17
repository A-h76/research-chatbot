import { api } from "@/lib/apiClient";
import type { Memory } from "@/types/api";

export const memoriesApi = {
  list: () => api.get<Memory[]>("/api/memories"),
  update: (id: number, body: { fact?: string; importance?: number }) =>
    api.patch<Memory>(`/api/memories/${id}`, body),
  remove: (id: number) => api.delete<{ ok: boolean }>(`/api/memories/${id}`),
};
