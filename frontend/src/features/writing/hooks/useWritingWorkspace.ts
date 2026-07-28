import { useMemo } from "react";
import { useUI } from "@/context/UIContext";

/** Slice 0 scaffold hook: project-scoped writing workspace guard. */
export function useWritingWorkspace() {
  const { currentProjectId } = useUI();
  return useMemo(
    () => ({
      projectId: currentProjectId,
      isProjectSelected: currentProjectId != null,
    }),
    [currentProjectId],
  );
}

