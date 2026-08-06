import type { UserFile } from "@/types/api";

export type PaperAnalysisStatus = "pending" | "running" | "done" | "failed";

/** Matches backend gate for cross-paper project research. */
export function paperAnalysisStatus(file: UserFile): PaperAnalysisStatus {
  const s = file.paper_analysis_status;
  if (s === "done" || s === "running" || s === "failed" || s === "pending") {
    return s;
  }
  return "pending";
}

export function isCrossPaperResearchReady(file: UserFile): boolean {
  if (file.cross_paper_research_ready === true) return true;
  return paperAnalysisStatus(file) === "done";
}

export function summarizeCrossPaperReadiness(files: UserFile[]) {
  const readyFiles = files.filter(isCrossPaperResearchReady);
  return {
    total: files.length,
    readyCount: readyFiles.length,
    pendingCount: files.length - readyFiles.length,
    readyFiles,
  };
}
