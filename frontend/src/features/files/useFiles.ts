import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { filesApi, type LibraryListParams } from "./api";
import type { UserFile } from "@/types/api";

// ── Library list (paginated + filtered) ──────────────────────────────────────
export function useFiles(params: LibraryListParams = {}) {
  return useQuery({
    queryKey: [...queryKeys.files, params],
    queryFn:  () => filesApi.list(params),
  });
}

// Convenience: flat list of all files (used by chat attachment picker etc.)
export function useAllFiles() {
  return useQuery({
    queryKey: [...queryKeys.files, "all"],
    queryFn:  () => filesApi.listAll(),
  });
}

// ── Library metadata ──────────────────────────────────────────────────────────
export function useLibraryTags(projectId?: number | null) {
  return useQuery({
    queryKey: ["library", "tags", projectId ?? null],
    queryFn:  () => filesApi.tags(projectId),
  });
}

export function useLibraryStats(projectId?: number | null) {
  return useQuery({
    queryKey: ["library", "stats", projectId ?? null],
    queryFn:  () => filesApi.stats(projectId),
  });
}

// ── Single file ───────────────────────────────────────────────────────────────
export function useFile(id: number | null) {
  return useQuery({
    queryKey: id ? queryKeys.file(id) : ["files", "none"],
    queryFn:  () => filesApi.get(id!),
    enabled:  id !== null,
  });
}

export function usePaperAnalysis(fileId: number | null, enabled = true) {
  return useQuery({
    queryKey: fileId ? queryKeys.fileAnalysis(fileId) : ["files", "none", "analysis"],
    queryFn:  () => filesApi.getAnalysis(fileId!),
    enabled:  fileId !== null && enabled,
    // Poll every 3 s while the backend is still working
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "pending" || s === "running" ? 3000 : false;
    },
  });
}

// Polls GET /api/uploads/batch/<id>/status every 2s while the batch is
// still in flight; stops the moment the backend reports "done" (a
// terminal batch state — see BulkBatchStatus's own doc comment for why
// there's no batch-level "failed" to also stop on). `retry: 3` overrides
// the app-wide default of 1 (lib/queryClient.ts) — a poll blip shouldn't
// tank the whole progress UI as fast as a one-off page load would.
export function useBulkUploadStatus(batchId: number | null) {
  return useQuery({
    queryKey: ["uploads", "batch", batchId ?? "none"],
    queryFn: () => filesApi.batchStatus(batchId!),
    enabled: batchId !== null,
    retry: 3,
    refetchInterval: (query) => (query.state.data?.status === "done" ? false : 2000),
  });
}

// ── Mutations ─────────────────────────────────────────────────────────────────
export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => filesApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.files });
      qc.invalidateQueries({ queryKey: ["library"] });
    },
  });
}

export function usePatchFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<UserFile> }) =>
      filesApi.patch(id, body),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: queryKeys.files });
      qc.invalidateQueries({ queryKey: ["library"] });
      qc.setQueryData(queryKeys.file(updated.id), updated);
    },
  });
}

export function useRefreshAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => filesApi.refreshAnalysis(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.fileAnalysis(id) });
    },
  });
}

// Writes to the same PaperAnalysis row refreshAnalysis does (see
// filesApi.analyzeDocument) — invalidate the same key so a subsequent visit
// to the paper overview page doesn't show stale cached data.
export function useAnalyzeDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => filesApi.analyzeDocument(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.fileAnalysis(id) });
    },
  });
}
