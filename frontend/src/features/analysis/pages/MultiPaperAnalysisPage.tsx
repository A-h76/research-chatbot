import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  FlaskConical,
  GitCompare,
  History,
  LayoutDashboard,
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
import { ResearchIntelligenceOverview } from "../components/ResearchIntelligenceOverview";
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
  | "overview"
  | "matrix"
  | "extract"
  | "themes"
  | "gaps"
  | "graph"
  | "timeline"
  | "methodology"
  | "compare";

const TAB_KEYS: Tab[] = [
  "overview",
  "matrix",
  "extract",
  "themes",
  "gaps",
  "graph",
  "timeline",
  "methodology",
  "compare",
];

const TAB_QUESTION: Partial<Record<Tab, string>> = {
  overview: "Where is this corpus?",
  matrix: "What does every paper say?",
  extract: "What has been extracted?",
  themes: "What topics emerge?",
  graph: "How are ideas connected?",
  timeline: "How has the field evolved?",
  gaps: "What's missing?",
  methodology: "Are methodologies strong?",
  compare: "How do studies differ?",
};

type TabDef = {
  key: Tab;
  label: string;
  icon: typeof Table2;
  group: "overview" | "understand" | "relationships" | "insights" | "generate";
};

function parseTab(raw: string | null): Tab {
  if (raw && (TAB_KEYS as string[]).includes(raw)) return raw as Tab;
  return "overview";
}

/** Research Intelligence workbench — Overview first, then progressive lenses. */
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
      setTabState("overview");
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
    if (next === "overview") params.delete("tab");
    else params.set("tab", next);
    setSearchParams(params, { replace: true });
    trackWorkflowEvent("analysis_view_opened", {
      projectId: currentProjectId,
      meta: { tab: next },
    });
  }

  const tabs: TabDef[] = [
    { key: "overview", label: "Overview", icon: LayoutDashboard, group: "overview" },
    { key: "matrix", label: "Evidence Matrix", icon: Table2, group: "understand" },
    { key: "extract", label: "Structured Evidence", icon: ClipboardList, group: "understand" },
    { key: "themes", label: "Themes", icon: Tags, group: "understand" },
    { key: "graph", label: "Graph", icon: Network, group: "relationships" },
    { key: "timeline", label: "Timeline", icon: History, group: "relationships" },
    { key: "gaps", label: "Research Gaps", icon: SearchX, group: "insights" },
    { key: "methodology", label: "Method Review", icon: FlaskConical, group: "insights" },
    ...(showAiCompare
      ? [
          {
            key: "compare" as const,
            label: "Compare Papers",
            icon: GitCompare,
            group: "generate" as const,
          },
        ]
      : []),
  ];

  const groups: { id: TabDef["group"]; label: string | null }[] = [
    { id: "overview", label: null },
    { id: "understand", label: "Understand" },
    { id: "relationships", label: "Relationships" },
    { id: "insights", label: "Insights" },
    { id: "generate", label: "Generate" },
  ];

  const question = TAB_QUESTION[tab];

  return (
    <PageContainer maxWidth="6xl" dense>
      <div className="mb-3 space-y-2 border-b border-border/70 pb-0">
        <div className="flex flex-wrap items-end gap-x-4 gap-y-2">
          {groups.map((g) => {
            const items = tabs.filter((t) => t.group === g.id);
            if (!items.length) return null;
            return (
              <div key={g.id} className="min-w-0">
                {g.label ? (
                  <p className="mb-0.5 px-1 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/70">
                    {g.label}
                  </p>
                ) : null}
                <div className="flex flex-wrap items-center gap-0.5">
                  {items.map(({ key, label, icon: Icon }) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setTab(key)}
                      title={TAB_QUESTION[key]}
                      className={cn(
                        "relative inline-flex h-9 items-center gap-1.5 px-2.5 text-[12px] font-medium",
                        tab === key
                          ? "text-foreground after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:rounded-full after:bg-primary"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      <Icon className="size-3.5 shrink-0" />
                      <span className="truncate">{label}</span>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
        {question ? (
          <p className="px-1 pb-2 text-[12px] text-muted-foreground">{question}</p>
        ) : null}
      </div>

      {tab === "overview" ? (
        <ResearchIntelligenceOverview
          projectId={currentProjectId}
          onOpenTab={setTab}
          showCompare={showAiCompare}
        />
      ) : tab === "matrix" ? (
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
