import { ApiError } from "@/lib/apiClient";

export function mapWritingError(error: unknown): string {
  if (!(error instanceof ApiError)) return "Unexpected writing error.";
  if (error.status === 409) return "Version conflict detected. Refresh before retrying.";
  if (error.status === 403) return "You do not have access to this document.";
  if (error.status === 404) return "Document not found.";
  if (error.status === 429) return "Too many requests. Please wait and retry.";
  if (error.code === "writing_assistant_failed" || error.status === 502) {
    return error.message || "Style transform failed. Check AI configuration and try again.";
  }
  if (error.code === "invalid_response") {
    return "Could not reach the writing assistant. Is the Flask backend running on :5000?";
  }
  return error.message || "Request failed.";
}

