import { ApiError } from "@/lib/apiClient";

export function mapWritingError(error: unknown): string {
  if (!(error instanceof ApiError)) return "Unexpected writing error.";
  if (error.status === 409) return "Version conflict detected. Refresh before retrying.";
  if (error.status === 403) return "You do not have access to this document.";
  if (error.status === 404) return "Document not found.";
  if (error.status === 429) return "Too many requests. Please wait and retry.";
  return error.message || "Request failed.";
}

