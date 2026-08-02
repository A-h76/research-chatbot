import { api } from "@/lib/apiClient";

export type ExportFormat = "json" | "md" | "txt" | "docx" | "pdf";

/** Triggers a browser download of the export (session cookie is sent automatically). */
export function downloadExport(format: ExportFormat, conversationId?: number) {
  const params = new URLSearchParams({ format });
  if (conversationId != null) params.set("conversation_id", String(conversationId));
  const a = document.createElement("a");
  a.href = `/api/export?${params.toString()}`;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export const settingsApi = {
  deleteAllChats: () =>
    api.post<{ ok: boolean; deleted: number }>("/api/conversations/delete", { all: true }),
  /** Step-up reauth: password accounts send password; OAuth-only send matching email. */
  deleteAccount: (body: { confirm: "DELETE"; password?: string; email?: string }) =>
    api.delete<{ ok: boolean }>("/api/account", body),
};
