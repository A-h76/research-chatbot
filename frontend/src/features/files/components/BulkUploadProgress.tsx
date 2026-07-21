import { useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useBulkUploadStatus } from "../useFiles";
import type { BulkBatchStatus, BulkBatchStatusJob } from "../api";

export interface BulkUploadProgressProps {
  batchId: string;
  // Passed the final batch payload (jobs[] included) rather than a bare
  // signal — callers that attached these files to something else (e.g. an
  // outgoing chat message) need each job's file_id/status to reconcile
  // their own state, not just "it's done".
  onComplete?: (data: BulkBatchStatus) => void;
  onError?: (error: string) => void;
}

type DisplayStatus = "pending" | "processing" | "completed" | "failed";

// Per-job status (pending|running|done|failed, see BulkBatchStatusJob) is
// distinct from the batch-level vocabulary (pending|processing|done) — this
// covers both so a row always gets a sensible icon regardless of which one
// it's fed.
const JOB_STATUS_ICON: Record<string, string> = {
  pending: "⏳",
  running: "🔄",
  processing: "🔄",
  done: "✅",
  completed: "✅",
  failed: "❌",
};

const STATUS_BADGE: Record<
  DisplayStatus,
  { label: string; variant: "secondary" | "default" | "destructive" }
> = {
  pending: { label: "Pending", variant: "secondary" },
  processing: { label: "Processing", variant: "default" },
  completed: { label: "Completed", variant: "default" },
  failed: { label: "Failed", variant: "destructive" },
};

export function BulkUploadProgress({ batchId, onComplete, onError }: BulkUploadProgressProps) {
  const numericBatchId = Number(batchId);
  const invalidBatchId = batchId.trim() === "" || !Number.isFinite(numericBatchId) || numericBatchId <= 0;

  // useBulkUploadStatus (features/files/useFiles.ts) polls GET
  // /api/uploads/batch/<id>/status every 2s via refetchInterval, retries a
  // failed poll up to 3 times, and stops automatically once status is
  // "done" — no manual setInterval/cleanup needed, React Query owns that
  // lifecycle (including cancelling on unmount).
  const { data, isLoading, isError, error } = useBulkUploadStatus(invalidBatchId ? null : numericBatchId);

  // The backend never reports a batch as a whole "failed" — a batch that
  // finishes with some failed files is still "done" (see BulkBatchStatus's
  // doc comment); those per-file failures are surfaced in the list below
  // instead. "failed" here means this progress UI itself lost track of the
  // batch: a bad id, or the status endpoint erroring out after retries.
  const displayStatus: DisplayStatus =
    invalidBatchId || isError
      ? "failed"
      : data?.status === "done"
        ? "completed"
        : data?.status === "processing"
          ? "processing"
          : "pending";

  const errorMessage = invalidBatchId
    ? "Invalid batch ID."
    : isError
      ? error instanceof Error
        ? error.message
        : "Failed to load batch status."
      : null;

  const totalFiles = data?.total_files ?? 0;
  const processedFiles = data?.processed_files ?? 0;
  const failedFiles = data?.failed_files ?? 0;
  const jobs = data?.jobs ?? [];
  const percent = totalFiles > 0 ? Math.round((processedFiles / totalFiles) * 100) : 0;
  const done = displayStatus === "completed" || displayStatus === "failed";

  // Fire exactly once per terminal transition, not on every poll tick while
  // still pending/processing.
  useEffect(() => {
    if (displayStatus === "completed" && data) onComplete?.(data);
    else if (displayStatus === "failed" && errorMessage) onError?.(errorMessage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayStatus]);

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>Bulk upload</CardTitle>
          <Badge variant={STATUS_BADGE[displayStatus].variant}>{STATUS_BADGE[displayStatus].label}</Badge>
        </div>
        <CardDescription>
          {invalidBatchId
            ? "This upload batch could not be found."
            : isLoading
              ? "Loading batch status…"
              : `${processedFiles} of ${totalFiles} file${totalFiles === 1 ? "" : "s"} processed`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {errorMessage ? (
          <p className="text-sm text-destructive">{errorMessage}</p>
        ) : (
          <>
            <Progress value={isLoading ? 0 : percent} />
            {failedFiles > 0 && (
              <p className="text-sm text-destructive">
                {failedFiles} file{failedFiles === 1 ? "" : "s"} failed to process.
              </p>
            )}
            <ul className="space-y-1.5">
              {jobs.map((job) => (
                <JobRow key={job.job_id} job={job} />
              ))}
            </ul>
          </>
        )}

        {done && (
          <Button
            size="sm"
            variant="outline"
            className="w-full"
            onClick={() =>
              displayStatus === "completed" && data
                ? onComplete?.(data)
                : onError?.(errorMessage ?? "Upload failed")
            }
          >
            {displayStatus === "completed" ? "Done" : "Close"}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function JobRow({ job }: { job: BulkBatchStatusJob }) {
  return (
    <li className="flex items-start gap-2 text-sm">
      <span className="shrink-0" aria-hidden="true">
        {JOB_STATUS_ICON[job.status] ?? "⏳"}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate">{job.filename}</span>
        {job.status === "failed" && job.error && (
          <span className="block text-xs text-destructive">{job.error}</span>
        )}
      </span>
    </li>
  );
}
