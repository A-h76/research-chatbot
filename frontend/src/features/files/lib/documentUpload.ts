import { isDocumentUpload } from "../api";

/** `<input accept>` for Library / document bulk uploads. */
export const DOCUMENT_ACCEPT = ".pdf,.epub,.docx,.txt";

/** Soft client cap — server MAX_BATCH_SIZE defaults to 50. */
export const MAX_LIBRARY_UPLOAD_FILES = 50;

export function partitionDocumentFiles(files: File[]): {
  accepted: File[];
  rejected: File[];
} {
  const accepted: File[] = [];
  const rejected: File[] = [];
  for (const file of files) {
    if (isDocumentUpload(file.name)) accepted.push(file);
    else rejected.push(file);
  }
  return { accepted, rejected };
}
