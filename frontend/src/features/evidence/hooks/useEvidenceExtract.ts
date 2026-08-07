import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "@/components/common/Toast";
import { formatApiFailure } from "@/lib/apiErrors";
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
  const openRi = {
    label: "Open Research Intelligence",
    onClick: () => {
      window.location.assign("/research/compare");
    },
  };

  if (data.status === "pending" || data.status === "queued") {
    toast.success("Evidence Extraction queued", {
      description: "Research Intelligence will update when extraction finishes.",
      action: openRi,
    });
    return;
  }
  if (data.status === "skipped" || data.skipped) {
    const reason = data.reason || "skipped";
    if (reason === "not_research_ready") {
      toast.error(
        "Paper needs full text first — use Retry Full Text or Attach PDF on the paper page",
      );
      return;
    }
    if (reason === "missing_phase1") {
      toast.error("Phase 1 analysis is missing — run analysis first");
      return;
    }
    toast.success(
      reason === "already_applied" || reason === "idempotent_reuse"
        ? "Already extracted (up to date)"
        : `Skipped: ${reason}`,
      reason === "already_applied" || reason === "idempotent_reuse"
        ? { action: openRi }
        : undefined,
    );
    return;
  }
  if (data.status === "succeeded" && data.reason === "idempotent_reuse") {
    toast.success("Already extracted (up to date)", { action: openRi });
    return;
  }
  if (created > 0) {
    toast.success("Research Intelligence ready", {
      description: `${created} evidence candidate${created === 1 ? "" : "s"} created — explore themes, gaps, and the matrix.`,
      action: openRi,
      duration: 8000,
    });
    return;
  }
  toast.success("Evidence Extraction finished (no new candidates)", {
    action: openRi,
  });
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
      toast.error(formatApiFailure(err, "Evidence extraction failed"));
    },
  });
}
