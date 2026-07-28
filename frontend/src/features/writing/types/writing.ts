export type WritingDocState = "draft" | "active" | "archived" | "deleted" | "purged";

export interface WritingDocumentView {
  id: number;
  projectId: number;
  title: string;
  content: string;
  state: WritingDocState;
  currentVersion: number;
  updatedAt: string | null;
}

export interface WritingVersionView {
  id: number;
  documentId: number;
  versionNo: number;
  source: "create" | "save" | "autosave" | "restore";
  createdAt: string | null;
}

export type AutosaveState = "idle" | "dirty" | "scheduled" | "saving" | "saved" | "retrying" | "conflict" | "failed";

export interface ConflictStateView {
  hasConflict: boolean;
  message: string;
  serverVersion?: number;
}

