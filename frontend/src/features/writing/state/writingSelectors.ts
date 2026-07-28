import type { WritingStoreState } from "./writingStore";

export const writingSelectors = {
  selectedDocumentId: (s: WritingStoreState) => s.selectedDocumentId,
  isDirty: (s: WritingStoreState) => s.isDirty,
  autosaveState: (s: WritingStoreState) => s.autosaveState,
  hasConflict: (s: WritingStoreState) => s.conflict.hasConflict,
};

