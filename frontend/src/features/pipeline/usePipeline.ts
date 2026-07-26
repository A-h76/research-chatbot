import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { adaptPipeline } from "./adapter";
import { pipelineApi } from "./api";
import type {
  AnalyzeResponse,
  PipelineDerived,
  PipelineDocument,
  PipelinePhaseName,
  StartAnalysisBody,
} from "./types";

const POLL_MS = 2500;

function shouldPollPipeline(doc: PipelineDocument | null | undefined): boolean {
  if (!doc) return false;
  return doc.status === "pending" || doc.status === "running";
}

export type UsePipelineOptions = {
  enabled?: boolean;
  /** When true, poll while status is pending/running. Default true. */
  poll?: boolean;
  /** Forwarded to adaptPipeline (hash mismatch → stale). */
  fileContentHash?: string | null;
};

/**
 * GET /api/documents/:id/pipeline — `data` is null when Phase 1 has never run (404).
 */
export function usePipeline(fileId: number | null, options: UsePipelineOptions = {}) {
  const { enabled = true, poll = true, fileContentHash } = options;
  const [enqueuePending, setEnqueuePending] = useState(false);
  const enqueueRef = useRef(false);

  const query = useQuery({
    queryKey: fileId != null ? queryKeys.pipeline(fileId) : ["pipeline", "none"],
    queryFn: () => pipelineApi.getPipeline(fileId!),
    enabled: fileId != null && enabled,
    retry: 1,
    refetchInterval: (q) => {
      if (!poll) return false;
      if (enqueueRef.current && q.state.data == null) return POLL_MS;
      return shouldPollPipeline(q.state.data) ? POLL_MS : false;
    },
  });

  // Clear enqueue flag once we see a row or a terminal state
  useEffect(() => {
    if (!enqueuePending) return;
    const doc = query.data;
    if (doc && (doc.status === "done" || doc.status === "failed" || doc.status === "partial")) {
      setEnqueuePending(false);
      enqueueRef.current = false;
    } else if (doc && (doc.status === "running" || doc.phases.length > 0)) {
      setEnqueuePending(false);
      enqueueRef.current = false;
    }
  }, [enqueuePending, query.data]);

  const derived: PipelineDerived = useMemo(
    () =>
      adaptPipeline(query.data ?? null, {
        fileContentHash,
        enqueuePending,
      }),
    [query.data, fileContentHash, enqueuePending],
  );

  return {
    ...query,
    /** Raw pipeline document or null if absent. */
    pipeline: query.data ?? null,
    /** Derived flags for future AI State Language / badges (M3). */
    derived,
    /** Mark that analyze was queued so adapter can show queued before first row. */
    markEnqueued: () => {
      enqueueRef.current = true;
      setEnqueuePending(true);
    },
    clearEnqueued: () => {
      enqueueRef.current = false;
      setEnqueuePending(false);
    },
  };
}

export type UsePipelinePhaseOptions = {
  enabled?: boolean;
};

/** GET /api/documents/:id/phases/:phase */
export function usePipelinePhase(
  fileId: number | null,
  phase: PipelinePhaseName | null,
  options: UsePipelinePhaseOptions = {},
) {
  const { enabled = true } = options;
  return useQuery({
    queryKey:
      fileId != null && phase
        ? queryKeys.pipelinePhase(fileId, phase)
        : ["pipeline", "none", "phase"],
    queryFn: () => pipelineApi.getPhase(fileId!, phase!),
    enabled: fileId != null && phase != null && enabled,
    retry: 1,
  });
}

/**
 * POST /api/documents/:id/analyze — invalidates pipeline (+ optional phase) caches.
 */
export function useStartAnalysis() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      documentId,
      ...body
    }: { documentId: number } & StartAnalysisBody): Promise<AnalyzeResponse> =>
      pipelineApi.startAnalysis(documentId, body),
    onSuccess: (data, vars) => {
      const id = vars.documentId;
      if (data.status === "queued") {
        // Keep polling until worker writes a row
        void qc.invalidateQueries({ queryKey: queryKeys.pipeline(id) });
        return;
      }
      // Sync path returned full document — seed cache
      qc.setQueryData(queryKeys.pipeline(id), data);
      void qc.invalidateQueries({ queryKey: ["pipeline", id] });
    },
  });
}

/** Invalidate pipeline + all cached phases for a document. */
export function useInvalidatePipeline() {
  const qc = useQueryClient();
  return (fileId: number) => {
    void qc.invalidateQueries({ queryKey: queryKeys.pipeline(fileId) });
    void qc.invalidateQueries({ queryKey: ["pipeline", fileId, "phase"] });
  };
}
