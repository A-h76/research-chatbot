import { useMemo } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { useAllFiles } from "@/features/files/useFiles";
import { useUI } from "@/context/UIContext";
import { CompareGapsWorkbench } from "../components/CompareGapsWorkbench";

/** D7 T4 — Compare & Gaps tool: toolbar + dense picker + exportable results. */
export function MultiPaperAnalysisPage() {
  const { currentProjectId } = useUI();
  const { data: allFilesRaw } = useAllFiles();
  const allFiles = useMemo(
    () => (allFilesRaw ?? []).filter((f) => f.kind === "document" && f.meta_status === "done"),
    [allFilesRaw],
  );

  return (
    <PageContainer title="Compare & Gaps" maxWidth="6xl" dense>
      <CompareGapsWorkbench files={allFiles} projectId={currentProjectId} />
    </PageContainer>
  );
}
