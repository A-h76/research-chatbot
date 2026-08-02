import type { DashboardData } from "./api";
import type { WritingDocument } from "@/types/api";

export type HomeStage = 1 | 2 | 3;

export type ChecklistItem = {
  id: string;
  label: string;
  href: string;
  done: boolean;
};

export function deriveHomeStage(opts: {
  totalPapers: number;
  projectCount: number;
  chatCount: number;
  analysed: number;
  writingCount: number;
}): HomeStage {
  if (opts.totalPapers === 0) return 1;
  const activeSignals =
    (opts.projectCount > 0 ? 1 : 0) +
    (opts.writingCount > 0 ? 1 : 0) +
    (opts.chatCount > 0 ? 1 : 0) +
    (opts.analysed > 0 ? 1 : 0) +
    (opts.totalPapers >= 3 ? 1 : 0);
  if (activeSignals >= 3 && opts.projectCount > 0) return 3;
  return 2;
}

export function buildGettingStarted(data: DashboardData): ChecklistItem[] {
  const hasPaper = data.library.total_papers > 0;
  const hasSummary = (data.library.analysed ?? 0) > 0;
  const hasChat = data.recent_chats.length > 0;
  const hasProject = data.projects.length > 0;

  return [
    { id: "account", label: "Create account", href: "/settings/account", done: true },
    { id: "upload", label: "Upload first paper", href: "/library?upload=1#import", done: hasPaper },
    {
      id: "summary",
      label: "Generate first summary",
      href: (() => {
        const id = data.recent_papers[0]?.id ?? data.current_papers[0]?.id;
        return id ? `/papers/${id}` : "/library?upload=1#import";
      })(),
      done: hasSummary,
    },
    {
      id: "question",
      label: "Ask your first research question",
      href: "/chat",
      done: hasChat,
    },
    {
      id: "project",
      label: "Create first project",
      href: "/projects?new=1",
      done: hasProject,
    },
  ];
}

export function literatureReviews(docs: WritingDocument[]): WritingDocument[] {
  return docs.filter((d) => {
    const t = (d.title || "").toLowerCase();
    const s = (d.status || "").toLowerCase();
    return (
      t.includes("literature") ||
      t.includes("review") ||
      t.includes("lit review") ||
      s.includes("review")
    );
  });
}
