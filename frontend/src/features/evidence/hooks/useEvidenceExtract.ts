import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "@/components/common/Toast";
import { ApiError } from "@/lib/apiClient";
import { evidenceApi } from "../api";

export type ExtractResult = {
  status?: string;
  created?: number;
  skipped?: boolean;
  reason?: string;
  run_id?: number | null;
  job_id?: number | null;
  objects_created?: number;
  candidate_count?: number;
};

function toastFromResult(data: ExtractResult) {
  const created = data.objects_created ?? data.created ?? data.candidate_count ?? 0;
  if (data.status === "pending" || data.status === "queued") {
    toast.success("Evidence Extraction queued");
    return;
  }
  if (data.status === "skipped" || data.skipped) {
    const reason = data.reason || "skipped";
    if (reason === "not_research_ready") {
      toast.error("Paper is not Research Ready yet");
      return;
    }
    if (reason === "missing_phase1") {
      toast.error("Phase 1 analysis is missing — run analysis first");
      return;
    }
    toast.success(reason === "already_applied" || reason === "idempotent_reuse" ? "Already extracted (up to date)" : `Skipped: ${reason}`);
    return;
  }
  if (data.status === "succeeded" && data.reason === "idempotent_reuse") {
    toast.success("Already extracted (up to date)");
    return;
  }
  toast.success(
    created > 0
      ? `Evidence Extraction created ${created} candidate object${created === 1 ? "" : "s"}`
      : "Evidence Extraction finished (no new candidates)",
  );
}

export function useEvidenceExtract() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (opts: { projectId: number; fileId: number; force?: boolean }) =>
      evidenceApi.extract(opts.projectId, opts.fileId, opts.force ?? false) as Promise<ExtractResult>,
    onSuccess: (data) => {
      toastFromResult(data);
      void qc.invalidateQueries({ queryKey: ["evidence"] });
      void qc.invalidateQueries({ queryKey: ["files"] });
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        toast.error(err.message || "Evidence extraction failed");
        return;
      }
      toast.error(err instanceof Error ? err.message : "Evidence extraction failed");
    },
  });
}
