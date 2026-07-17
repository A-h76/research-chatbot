import { api } from "@/lib/apiClient";
import type { ComparisonResult, GapFinderResult } from "@/types/api";

export interface CompareInput {
  file_ids: number[];
  project_id?: number | null;
  force?: boolean;
}

export const analysisApi = {
  // ── Comparison (M11) ──
  compare:          (body: CompareInput) =>
                      api.post<ComparisonResult>("/api/analysis/compare", body),
  getComparison:    (id: number) =>
                      api.get<ComparisonResult>(`/api/analysis/compare/${id}`),
  deleteComparison: (id: number) =>
                      api.delete<{ ok: boolean }>(`/api/analysis/compare/${id}`),

  // ── Gap Finder (M12) ──
  findGaps:    (body: CompareInput) =>
                 api.post<GapFinderResult>("/api/analysis/gaps", body),
  getGaps:     (id: number) =>
                 api.get<GapFinderResult>(`/api/analysis/gaps/${id}`),
  deleteGaps:  (id: number) =>
                 api.delete<{ ok: boolean }>(`/api/analysis/gaps/${id}`),
};
