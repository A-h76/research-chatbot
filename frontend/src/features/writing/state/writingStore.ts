import type { AutosaveState, ConflictStateView } from "../types/writing";

export interface WritingStoreState {
  selectedDocumentId: number | null;
  isDirty: boolean;
  autosaveState: AutosaveState;
  optimisticVersion: number | null;
  conflict: ConflictStateView;
}

export const initialWritingStoreState: WritingStoreState = {
  selectedDocumentId: null,
  isDirty: false,
  autosaveState: "idle",
  optimisticVersion: null,
  conflict: { hasConflict: false, message: "" },
};

