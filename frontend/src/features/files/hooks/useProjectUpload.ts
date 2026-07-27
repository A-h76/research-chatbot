import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { toast } from "@/components/common/Toast";
import { filesApi } from "../api";
import {
  MAX_LIBRARY_UPLOAD_FILES,
  partitionDocumentFiles,
} from "../lib/documentUpload";
import type { LibraryUploadItem, LibraryUploadStatus } from "./useLibraryUpload";

function tempKey() {
  return `tmp:${crypto.randomUUID()}`;
}

/** Upload documents scoped to a project (sets project_id on each file). */
export function useProjectUpload(projectId: number) {
  const qc = useQueryClient();
  const [items, setItems] = useState<LibraryUploadItem[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const upload = useCallback(
    async (fileList: File[] | FileList) => {
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
          status: "uploading" as LibraryUploadStatus,
          error: null,
        })),
        ...prev,
      ]);

      setSubmitting(true);
      try {
        for (let i = 0; i < toSend.length; i++) {
          const file = toSend[i]!;
          const key = pendingKeys[i]!;
          try {
            const outcome = await filesApi.upload(file, null, projectId);
            const fileId =
              outcome.async === false
                ? outcome.result.id
                : outcome.result.document_id;
            setItems((prev) =>
              prev.map((item) =>
                item.key === key
                  ? { ...item, fileId, status: "uploaded", error: null }
                  : item,
              ),
            );
          } catch (err) {
            const message = err instanceof Error ? err.message : "Upload failed";
            setItems((prev) =>
              prev.map((item) =>
                item.key === key ? { ...item, status: "failed", error: message } : item,
              ),
            );
            toast.error(`${file.name}: ${message}`);
          }
        }
        void qc.invalidateQueries({ queryKey: queryKeys.files });
        void qc.invalidateQueries({ queryKey: queryKeys.projectHub(projectId) });
        void qc.invalidateQueries({ queryKey: ["library"] });
        toast.success(
          toSend.length === 1
            ? `Uploaded ${toSend[0]!.name}`
            : `Uploaded ${toSend.length} papers`,
        );
      } finally {
        setSubmitting(false);
      }
    },
    [projectId, qc],
  );

  const clearFinished = useCallback(() => {
    setItems((prev) => prev.filter((i) => i.status === "uploading"));
  }, []);

  return {
    items,
    isUploading: submitting || items.some((i) => i.status === "uploading"),
    upload,
    clearFinished,
  };
}
