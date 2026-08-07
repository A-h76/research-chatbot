import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageContainer } from "@/components/layout/PageContainer";
import { useAllFiles } from "@/features/files/useFiles";
import { useUI } from "@/context/UIContext";
import { CompareGapsWorkbench } from "../components/CompareGapsWorkbench";
import { ResearchIntelligenceOverview } from "../components/ResearchIntelligenceOverview";
import { ResearchIntelligenceNav } from "../components/ResearchIntelligenceNav";
import { ResearchIntelligenceCategoryLanding } from "../components/ResearchIntelligenceCategoryLanding";
import { EvidenceMatrixPanel } from "@/features/evidence/components/EvidenceMatrixPanel";
import { EvidenceThemesPanel } from "@/features/evidence/components/EvidenceThemesPanel";
import { EvidenceGraphPanel } from "@/features/evidence/components/EvidenceGraphPanel";
import { EvidenceGapsPanel } from "@/features/evidence/components/EvidenceGapsPanel";
import { EvidenceTimelinePanel } from "@/features/evidence/components/EvidenceTimelinePanel";
import { EvidenceMethodologyPanel } from "@/features/evidence/components/EvidenceMethodologyPanel";
import { StructuredExtractPanel } from "@/features/evidence/components/StructuredExtractPanel";
import { trackWorkflowEvent } from "@/lib/workflowTelemetry";
import { loadResearchPrefs } from "@/features/settings/lib/researchPrefs";
import { useRiCorpusMetrics } from "../hooks/useRiCorpusMetrics";
import {
  parseRiTab,
  type RiCategoryId,
  type RiTab,
} from "../researchIntelligenceNav";

const CATEGORY_IDS = new Set<string>([
  "understand",
  "relationships",
  "insights",
  "synthesis",
]);

/** Research Intelligence — workflow IA: Mission Control + category landings + lenses. */
export function MultiPaperAnalysisPage() {
  const { currentProjectId } = useUI();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTabState] = useState<RiTab>(() => parseRiTab(searchParams.get("tab")));
  const showAiCompare = loadResearchPrefs().showAiCompare;
  const metrics = useRiCorpusMetrics(currentProjectId);
  const { data: allFilesRaw } = useAllFiles();
  const allFiles = useMemo(
    () => (allFilesRaw ?? []).filter((f) => f.kind === "document" && f.meta_status === "done"),
    [allFilesRaw],
  );

  useEffect(() => {
    const next = parseRiTab(searchParams.get("tab"));
    if (next === "compare" && !showAiCompare) {
      setTabState("synthesis");
      const params = new URLSearchParams(searchParams);
      params.set("tab", "synthesis");
      setSearchParams(params, { replace: true });
      return;
    }
    setTabState(next);
  }, [searchParams, showAiCompare, setSearchParams]);

  function setTab(next: RiTab) {
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

  const landingMetrics = {
    papers: metrics.papers,
    evidence: metrics.evidence,
    themes: metrics.themes,
    gaps: metrics.gaps,
    methods: metrics.methods,
    coverage: metrics.coverage,
    contradictions: metrics.contradictions,
    unknownCells: metrics.unknownCells,
  };

  return (
    <PageContainer maxWidth="6xl" dense>
      <ResearchIntelligenceNav
        tab={tab}
        onOpenTab={setTab}
        showCompare={showAiCompare}
      />

      {tab === "overview" ? (
        <ResearchIntelligenceOverview
          projectId={currentProjectId}
          onOpenTab={setTab}
          showCompare={showAiCompare}
        />
      ) : CATEGORY_IDS.has(tab) ? (
        <ResearchIntelligenceCategoryLanding
          categoryId={tab as RiCategoryId}
          onOpenTab={setTab}
          metrics={landingMetrics}
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
