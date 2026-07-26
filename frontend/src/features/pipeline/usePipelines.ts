import { useQueries } from "@tanstack/react-query";
import { useMemo } from "react";
import { queryKeys } from "@/lib/queryKeys";
import { adaptPipeline } from "./adapter";
import { pipelineApi } from "./api";
import { resolveAiState, type AiStateResolved } from "./aiState";
import type { PipelineDerived, PipelineDocument } from "./types";

const POLL_MS = 2500;

function shouldPoll(doc: PipelineDocument | null | undefined) {
  if (!doc) return false;
  return doc.status === "pending" || doc.status === "running";
}

export type PipelineEntry = {
  fileId: number;
  pipeline: PipelineDocument | null;
  derived: PipelineDerived;
  aiState: AiStateResolved;
  isLoading: boolean;
  isError: boolean;
};

/**
 * Batch GET /pipeline for Library / Project lists (shared React Query keys with usePipeline).
 */
export function usePipelines(
  fileIds: number[],
  metaById?: Record<number, string | null | undefined>,
): {
  byId: Map<number, PipelineEntry>;
  isLoading: boolean;
} {
  const unique = useMemo(
    () => [...new Set(fileIds.filter((id) => Number.isFinite(id) && id > 0))],
    [fileIds],
  );

  // Stable key so meta changes retarget polling without identity thrash
  const metaKey = useMemo(
    () => unique.map((id) => `${id}:${metaById?.[id] ?? ""}`).join("|"),
    [unique, metaById],
  );

  const results = useQueries({
    queries: unique.map((fileId) => ({
      queryKey: queryKeys.pipeline(fileId),
      queryFn: () => pipelineApi.getPipeline(fileId),
      staleTime: 15_000,
      retry: 1,
      refetchInterval: (q: { state: { data: PipelineDocument | null | undefined } }) => {
        const meta = metaById?.[fileId];
        if (shouldPoll(q.state.data)) return POLL_MS;
        if (q.state.data == null && (meta === "pending" || meta === "running")) return POLL_MS;
        return false;
      },
    })),
  });

  const dataSig = results.map((r) => `${r.dataUpdatedAt}:${r.status}:${r.data?.status ?? "null"}`).join("|");

  const byId = useMemo(() => {
    const map = new Map<number, PipelineEntry>();
    unique.forEach((fileId, i) => {
      const r = results[i]!;
      const pipeline = (r.data ?? null) as PipelineDocument | null;
      const meta = metaById?.[fileId] ?? null;
      const derived = adaptPipeline(pipeline, {
        enqueuePending: pipeline == null && meta === "pending",
      });
      map.set(fileId, {
        fileId,
        pipeline,
        derived,
        aiState: resolveAiState({ derived, metaStatus: meta }),
        isLoading: r.isLoading,
        isError: r.isError,
      });
    });
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps -- dataSig / metaKey capture results
  }, [unique, dataSig, metaKey]);

  return {
    byId,
    isLoading: results.some((r) => r.isLoading),
  };
}
