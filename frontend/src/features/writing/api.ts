import { api } from "@/lib/apiClient";
import type { WritingAction, WritingResponse } from "@/types/api";

export const writingApi = {
  transform: (action: WritingAction, text: string) =>
    api.post<WritingResponse>("/api/writing", { action, text }),

  exportNotes: () =>
    `/api/export/notes`,  // POST — handled inline in the page

  exportAnalysisUrl: (fileId: number, format: "md" | "txt" | "docx") =>
    `/api/export/analysis/${fileId}?format=${format}`,

  exportChatUrl: (convId: number, format: "md" | "txt") =>
    `/api/export/chat/${convId}?format=${format}`,
};
