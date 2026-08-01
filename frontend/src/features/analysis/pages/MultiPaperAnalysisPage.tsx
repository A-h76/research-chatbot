import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  FlaskConical,
  GitCompare,
  History,
  Network,
  SearchX,
  Table2,
  Tags,
  ClipboardList,
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
import { StructuredExtractPanel } from "@/features/evidence/components/StructuredExtractPanel";
import { trackWorkflowEvent } from "@/lib/workflowTelemetry";
import { loadResearchPrefs } from "@/features/settings/lib/researchPrefs";
import { cn } from "@/lib/utils";

/** Evidence RI tabs are primary; LLM narrative compare is optional (settings). */
type Tab =
  | "matrix"
  | "extract"
  | "themes"
  | "gaps"
  | "graph"
  | "timeline"
  | "methodology"
  | "compare";

const TAB_KEYS: Tab[] = [
  "matrix",
  "extract",
  "themes",
  "gaps",
  "graph",
  "timeline",
  "methodology",
  "compare",
];

function parseTab(raw: string | null): Tab {
  if (raw && (TAB_KEYS as string[]).includes(raw)) return raw as Tab;
  return "matrix";
}

/** Research Intelligence workbench — evidence-first. Top bar names the place. */
export function MultiPaperAnalysisPage() {
  const { currentProjectId } = useUI();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTabState] = useState<Tab>(() => parseTab(searchParams.get("tab")));
  const showAiCompare = loadResearchPrefs().showAiCompare;
  const { data: allFilesRaw } = useAllFiles();
  const allFiles = useMemo(
    () => (allFilesRaw ?? []).filter((f) => f.kind === "document" && f.meta_status === "done"),
    [allFilesRaw],
  );

  useEffect(() => {
    const next = parseTab(searchParams.get("tab"));
    if (next === "compare" && !showAiCompare) {
      setTabState("matrix");
      const params = new URLSearchParams(searchParams);
      params.delete("tab");
      setSearchParams(params, { replace: true });
      return;
    }
    setTabState(next);
  }, [searchParams, showAiCompare, setSearchParams]);

  function setTab(next: Tab) {
    setTabState(next);
    const params = new URLSearchParams(searchParams);
    if (next === "matrix") params.delete("tab");
    else params.set("tab", next);
    setSearchParams(params, { replace: true });
    trackWorkflowEvent("analysis_view_opened", {
      projectId: currentProjectId,
      meta: { tab: next },
    });
  }

  const tabs = (
    [
      { key: "matrix" as const, label: "Matrix", icon: Table2 },
      { key: "extract" as const, label: "Extract", icon: ClipboardList },
      { key: "themes" as const, label: "Themes", icon: Tags },
      { key: "gaps" as const, label: "Gaps", icon: SearchX },
      { key: "graph" as const, label: "Graph", icon: Network },
      { key: "timeline" as const, label: "Timeline", icon: History },
      { key: "methodology" as const, label: "Methods", icon: FlaskConical },
      ...(showAiCompare
        ? [{ key: "compare" as const, label: "AI Compare", icon: GitCompare }]
        : []),
    ] as const
  );

  return (
    <PageContainer maxWidth="6xl" dense>
      <div className="mb-4 flex flex-wrap items-center gap-0.5 border-b border-border/70 pb-0">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={cn(
              "relative inline-flex h-9 items-center gap-1.5 px-2.5 text-[12px] font-medium",
              tab === key
                ? "text-foreground after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:rounded-full after:bg-primary"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="size-3.5" /> {label}
          </button>
        ))}
      </div>

      {tab === "matrix" ? (
        <EvidenceMatrixPanel projectId={currentProjectId} />
      ) : tab === "extract" ? (
        <StructuredExtractPanel projectId={currentProjectId} />
      ) : tab === "themes" ? (
        <EvidenceThemesPanel projectId={currentProjectId} />
      ) : tab === "gaps" ? (
        <EvidenceGapsPanel projectId={currentProjectId} />
      ) : tab === "graph" ? (
        <EvidenceGraphPanel projectId={currentProjectId} />
      ) : tab === "timeline" ? (
        <EvidenceTimelinePanel projectId={currentProjectId} />
      ) : tab === "methodology" ? (
        <EvidenceMethodologyPanel projectId={currentProjectId} />
      ) : (
        <CompareGapsWorkbench files={allFiles} projectId={currentProjectId} />
      )}
    </PageContainer>
  );
}
