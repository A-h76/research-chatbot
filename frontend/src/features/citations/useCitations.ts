import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { citationsApi, type CitationInput } from "./api";

export function useCitations(params: { project_id?: number | null; q?: string } = {}) {
  return useQuery({
    queryKey: [...queryKeys.citations, params],
    queryFn:  () => citationsApi.list(params),
  });
}

export function useCreateCitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CitationInput) => citationsApi.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.citations });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useUpdateCitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<CitationInput> }) =>
      citationsApi.update(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.citations }),
  });
}

export function useDeleteCitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => citationsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.citations });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useCitationFromPaper() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ fileId, projectId }: { fileId: number; projectId?: number | null }) =>
      citationsApi.fromPaper(fileId, projectId),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.citations }),
  });
}
