import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { toast } from "@/components/common/Toast";
import { filesApi } from "../api";
import { useBulkUploadStatus } from "../useFiles";
import {
  MAX_LIBRARY_UPLOAD_FILES,
  partitionDocumentFiles,
} from "../lib/documentUpload";

/** Upload lifecycle only (M2) — not AI pipeline states. */
export type LibraryUploadStatus = "uploading" | "uploaded" | "failed";

export interface LibraryUploadItem {
  /** Stable client key (temp or `file:${id}`). */
  key: string;
  filename: string;
  fileId: number | null;
  status: LibraryUploadStatus;
  error: string | null;
}

function tempKey() {
  return `tmp:${crypto.randomUUID()}`;
}

/**
 * Library document upload — reuses `filesApi.uploadFiles` + batch status polling.
 * Does not touch chat Composer or Phase 1 pipeline hooks.
 */
export function useLibraryUpload() {
  const qc = useQueryClient();
  const [items, setItems] = useState<LibraryUploadItem[]>([]);
  const [batchId, setBatchId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const keyByFileId = useRef<Map<number, string>>(new Map());

  const { data: batch } = useBulkUploadStatus(batchId);
  const completedBatchRef = useRef<number | null>(null);

  // Mirror batch job rows onto the queue (Uploading → Uploaded | Failed).
  useEffect(() => {
    if (!batch) return;

    setItems((prev) => {
      const byFileId = new Map(prev.filter((i) => i.fileId != null).map((i) => [i.fileId!, i]));
      const next = [...prev];

      for (const job of batch.jobs) {
        const existing = byFileId.get(job.file_id);
        const status: LibraryUploadStatus =
          job.status === "failed"
            ? "failed"
            : job.status === "done"
              ? "uploaded"
              : "uploading";
        const error = job.status === "failed" ? (job.error ?? "Upload failed") : null;

        if (existing) {
          const idx = next.findIndex((i) => i.key === existing.key);
          if (idx >= 0) {
            next[idx] = {
              ...existing,
              filename: job.filename,
              fileId: job.file_id,
              status,
              error,
            };
          }
        } else {
          const key = keyByFileId.current.get(job.file_id) ?? `file:${job.file_id}`;
          keyByFileId.current.set(job.file_id, key);
          next.push({
            key,
            filename: job.filename,
            fileId: job.file_id,
            status,
            error,
          });
        }
      }
      return next;
    });

    if (batch.status === "done" && completedBatchRef.current !== batch.batch_id) {
      completedBatchRef.current = batch.batch_id;
      void qc.invalidateQueries({ queryKey: queryKeys.files });
      void qc.invalidateQueries({ queryKey: ["library"] });

      const failed = batch.jobs.filter((j) => j.status === "failed");
      const ok = batch.jobs.filter((j) => j.status === "done");
      if (ok.length > 0) {
        toast.success(
          ok.length === 1
            ? `Uploaded ${ok[0]!.filename}`
            : `Uploaded ${ok.length} papers`,
        );
      }
      for (const j of failed) {
        toast.error(`${j.filename}: ${j.error ?? "failed"}`);
      }
      setBatchId(null);
    }
  }, [batch, qc]);

  const upload = useCallback(async (fileList: File[] | FileList) => {
    const files = Array.from(fileList);
    const { accepted, rejected } = partitionDocumentFiles(files);

    for (const file of rejected) {
      toast.error(`${file.name}: unsupported type (use PDF, EPUB, DOCX, or TXT)`);
    }
    if (accepted.length === 0) return;

    let toSend = accepted;
    if (toSend.length > MAX_LIBRARY_UPLOAD_FILES) {
      toast.info(
        `You selected ${toSend.length} files — uploading the first ${MAX_LIBRARY_UPLOAD_FILES}.`,
      );
      toSend = toSend.slice(0, MAX_LIBRARY_UPLOAD_FILES);
    }

    const pendingKeys = toSend.map(() => tempKey());
    setItems((prev) => [
      ...toSend.map((file, i) => ({
        key: pendingKeys[i]!,
        filename: file.name,
        fileId: null,
        status: "uploading" as const,
        error: null,
      })),
      ...prev,
    ]);

    setSubmitting(true);
    try {
      const { batch_id, jobs } = await filesApi.uploadFiles(toSend);
      setItems((prev) =>
        prev.map((item) => {
          const i = pendingKeys.indexOf(item.key);
          if (i === -1) return item;
          const job = jobs[i];
          if (!job) return { ...item, status: "failed", error: "No job returned" };
          keyByFileId.current.set(job.file_id, item.key);
          return {
            ...item,
            fileId: job.file_id,
            filename: job.filename,
            status: "uploading",
            error: null,
          };
        }),
      );
      setBatchId(batch_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setItems((prev) =>
        prev.map((item) =>
          pendingKeys.includes(item.key)
            ? { ...item, status: "failed", error: message }
            : item,
        ),
      );
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }, []);

  const clearFinished = useCallback(() => {
    setItems((prev) => prev.filter((i) => i.status === "uploading"));
  }, []);

  const isUploading =
    submitting || items.some((i) => i.status === "uploading") || batchId != null;

  const recentUploaded = items.filter((i) => i.status === "uploaded");
  const queue = items; // full session queue including failures

  return {
    items: queue,
    recentUploaded,
    isUploading,
    upload,
    clearFinished,
  };
}
