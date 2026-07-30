import { useMemo, useState } from "react";
import {
  FlaskConical,
  GitCompare,
  History,
  Network,
  SearchX,
  Table2,
  Tags,
} from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { useAllFiles } from "@/features/files/useFiles";
import { useUI } from "@/context/UIContext";
import { CompareGapsWorkbench } from "../components/CompareGapsWorkbench";
import { EvidenceMatrixPanel } from "@/features/evidence/components/EvidenceMatrixPanel";
import { EvidenceThemesPanel } from "@/features/evidence/components/EvidenceThemesPanel";
import { EvidenceGraphPanel } from "@/features/evidence/components/EvidenceGraphPanel";
import { EvidenceGapsPanel } from "@/features/evidence/components/EvidenceGapsPanel";
import { EvidenceTimelinePanel } from "@/features/evidence/components/EvidenceTimelinePanel";
import { EvidenceMethodologyPanel } from "@/features/evidence/components/EvidenceMethodologyPanel";
import { cn } from "@/lib/utils";

type Tab =
  | "compare"
  | "matrix"
  | "themes"
  | "gaps"
  | "graph"
  | "timeline"
  | "methodology";

const TITLES: Record<Tab, string> = {
  compare: "Compare & Gaps",
  matrix: "Evidence Matrix",
  themes: "Theme Discovery",
  gaps: "Research Gaps",
  graph: "Knowledge Graph",
  timeline: "Research Timeline",
  methodology: "Methodology",
};

/** Research Intelligence workbench — Compare + RI surfaces. */
export function MultiPaperAnalysisPage() {
  const { currentProjectId } = useUI();
  const [tab, setTab] = useState<Tab>("compare");
  const { data: allFilesRaw } = useAllFiles();
  const allFiles = useMemo(
    () => (allFilesRaw ?? []).filter((f) => f.kind === "document" && f.meta_status === "done"),
    [allFilesRaw],
  );

  return (
    <PageContainer title={TITLES[tab]} maxWidth="6xl" dense>
      <div className="mb-3 flex flex-wrap items-center gap-0.5 rounded-md border border-border p-0.5 w-fit">
        {(
          [
            { key: "compare" as const, label: "Compare", icon: GitCompare },
            { key: "matrix" as const, label: "Matrix", icon: Table2 },
            { key: "themes" as const, label: "Themes", icon: Tags },
            { key: "gaps" as const, label: "Gaps", icon: SearchX },
            { key: "graph" as const, label: "Graph", icon: Network },
            { key: "timeline" as const, label: "Timeline", icon: History },
            { key: "methodology" as const, label: "Methods", icon: FlaskConical },
          ] as const
        ).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={cn(
              "inline-flex h-8 items-center gap-1.5 rounded px-2.5 text-[12px] font-medium",
              tab === key
                ? "bg-muted text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="size-3.5" /> {label}
          </button>
        ))}
      </div>

      {tab === "compare" ? (
        <CompareGapsWorkbench files={allFiles} projectId={currentProjectId} />
      ) : tab === "matrix" ? (
        <EvidenceMatrixPanel projectId={currentProjectId} />
      ) : tab === "themes" ? (
        <EvidenceThemesPanel projectId={currentProjectId} />
      ) : tab === "gaps" ? (
        <EvidenceGapsPanel projectId={currentProjectId} />
      ) : tab === "graph" ? (
        <EvidenceGraphPanel projectId={currentProjectId} />
      ) : tab === "timeline" ? (
        <EvidenceTimelinePanel projectId={currentProjectId} />
      ) : (
        <EvidenceMethodologyPanel projectId={currentProjectId} />
      )}
    </PageContainer>
  );
}
