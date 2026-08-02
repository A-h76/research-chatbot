/**
 * Pure autosave scheduling / error classification for Writing Shell.
 * Kept free of React so conflict/offline edge cases are unit-testable.
 */

export type WritingSaveState =
  | "idle"
  | "dirty"
  | "scheduled"
  | "saving"
  | "saved"
  | "conflict"
  | "error";

/** True when a debounced autosave may be scheduled. */
export function shouldScheduleAutosave(opts: {
  isOffline: boolean;
  saveState: WritingSaveState;
}): boolean {
  if (opts.isOffline) return false;
  if (opts.saveState === "conflict") return false;
  return true;
}

/** Map API failure text to save-state bucket. */
export function classifyAutosaveFailure(message: string): "conflict" | "error" {
  const m = (message || "").toLowerCase();
  if (m.includes("version_conflict") || m.includes("409") || m.includes("stale_document_version")) {
    return "conflict";
  }
  return "error";
}

/** After coming back online, resume only if local draft still needs sync. */
export function shouldResumeAutosaveOnOnline(saveState: WritingSaveState): boolean {
  return saveState === "error" || saveState === "dirty" || saveState === "scheduled";
}
