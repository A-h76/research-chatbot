import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { analysisApi, type CompareInput } from "./api";

// ── Comparison (M11) ──────────────────────────────────────────────────────────
export function useComparison(id: number | null) {
  return useQuery({
    queryKey: id ? queryKeys.comparison(id) : ["analysis", "compare", "none"],
    queryFn:  () => analysisApi.getComparison(id!),
    enabled:  id !== null,
    refetchInterval: (query) =>
      query.state.data?.status === "running" ? 3000 : false,
  });
}

export function useCompare() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CompareInput) => analysisApi.compare(body),
    onSuccess: (result) => {
      qc.setQueryData(queryKeys.comparison(result.id), result);
    },
  });
}

export function useDeleteComparison() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => analysisApi.deleteComparison(id),
    onSuccess: (_data, id) => {
      qc.removeQueries({ queryKey: queryKeys.comparison(id) });
    },
  });
}

// ── Gap Finder (M12) ─────────────────────────────────────────────────────────
export function useGapResult(id: number | null) {
  return useQuery({
    queryKey: id ? queryKeys.gaps(id) : ["analysis", "gaps", "none"],
    queryFn:  () => analysisApi.getGaps(id!),
    enabled:  id !== null,
    refetchInterval: (query) =>
      query.state.data?.status === "running" ? 3000 : false,
  });
}

export function useFindGaps() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CompareInput) => analysisApi.findGaps(body),
    onSuccess: (result) => {
      qc.setQueryData(queryKeys.gaps(result.id), result);
    },
  });
}

export function useDeleteGaps() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => analysisApi.deleteGaps(id),
    onSuccess: (_data, id) => {
      qc.removeQueries({ queryKey: queryKeys.gaps(id) });
    },
  });
}
