import { useQuery } from "@tanstack/react-query";
import { evidenceApi } from "@/features/evidence/api";
import { useProjectConsensusConflict } from "@/features/evidence/hooks/useProjectConsensusConflict";
import { useAllFiles } from "@/features/files/useFiles";
import { useMemo } from "react";

export type RiCorpusMetrics = {
  papers: number;
  evidence: number;
  themes: number;
  gaps: number;
  methods: number;
  coverage: number | null;
  contradictions: number;
  unknownCells: number;
  papersWithEvidence: number;
  loading: boolean;
  themeLabels: string[];
  gapStatements: string[];
  hasConflict: boolean;
  conflictSummary: string | null;
};

/** Shared corpus signals for Mission Control + category landings. */
export function useRiCorpusMetrics(projectId: number | null): RiCorpusMetrics {
  const enabled = projectId != null;
  const { data: allFiles } = useAllFiles();
  const paperCount = useMemo(() => {
    if (!enabled) return 0;
    return (allFiles ?? []).filter(
      (f) =>
        f.kind === "document" &&
        f.meta_status === "done" &&
        (f.project_id == null || f.project_id === projectId),
    ).length;
  }, [allFiles, enabled, projectId]);

  const matrixQ = useQuery({
    queryKey: ["evidence", "matrix", projectId, ""],
    queryFn: () => evidenceApi.matrix(projectId as number),
    enabled,
    staleTime: 30_000,
  });
  const themesQ = useQuery({
    queryKey: ["evidence", "themes", projectId, ""],
    queryFn: () => evidenceApi.themes(projectId as number),
    enabled,
    staleTime: 30_000,
  });
  const gapsQ = useQuery({
    queryKey: ["evidence", "gaps", projectId],
    queryFn: () => evidenceApi.gaps(projectId as number),
    enabled,
    staleTime: 30_000,
  });
  const methodologyQ = useQuery({
    queryKey: ["evidence", "methodology", projectId, ""],
    queryFn: () => evidenceApi.methodology(projectId as number),
    enabled,
    staleTime: 30_000,
  });
  const graphQ = useQuery({
    queryKey: ["evidence", "graph", projectId],
    queryFn: () => evidenceApi.graph(projectId as number),
    enabled,
    staleTime: 30_000,
  });
  const ri = useProjectConsensusConflict({ projectId, enabled });

  const loading =
    enabled &&
    (matrixQ.isLoading ||
      themesQ.isLoading ||
      gapsQ.isLoading ||
      methodologyQ.isLoading ||
      graphQ.isLoading);

  const papers = Math.max(paperCount, matrixQ.data?.metrics.paper_count ?? 0);
  const evidence =
    gapsQ.data?.metrics.evidence_count ??
    matrixQ.data?.metrics.papers_with_evidence ??
    0;
  const themes = themesQ.data?.metrics.theme_count ?? 0;
  const methods = methodologyQ.data?.metrics.card_count ?? 0;
  const gaps = gapsQ.data?.metrics.gap_count ?? 0;
  const coverage = matrixQ.data?.metrics.coverage ?? null;
  const unknownCells = matrixQ.data?.metrics.cell_unknown ?? 0;
  const papersWithEvidence = matrixQ.data?.metrics.papers_with_evidence ?? 0;
  const contradictions =
    graphQ.data?.metrics.contradicts_count ??
    (ri.conflict?.has_conflict ? 1 : 0);

  return {
    papers,
    evidence,
    themes,
    gaps,
    methods,
    coverage,
    contradictions,
    unknownCells,
    papersWithEvidence,
    loading,
    themeLabels: (themesQ.data?.themes ?? []).slice(0, 4).map((t) => t.label),
    gapStatements: (gapsQ.data?.gaps ?? []).slice(0, 3).map((g) => g.statement),
    hasConflict: Boolean(ri.conflict?.has_conflict),
    conflictSummary: ri.conflict?.product_summary ?? null,
  };
}
