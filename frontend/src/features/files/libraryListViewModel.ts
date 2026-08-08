/**
 * Library list view model — Constitution: Invisible Intelligence.
 * Answers: "Which papers matter?"
 * Continue reading · Needs attention · calm list. No KPI dump.
 */

import type { UserFile } from "@/types/api";

export type LibraryAttentionKind = "needs_pdf" | "failed" | "processing";

export type LibraryAttentionRow = {
  file: UserFile;
  kind: LibraryAttentionKind;
  label: string;
  actionLabel: string;
};

export type LibraryListView = {
  continuePaper: UserFile | null;
  attentionRows: LibraryAttentionRow[];
  attentionTotal: number;
};

function isNeedsPdf(f: UserFile): boolean {
  if (f.kind !== "document") return false;
  if (f.has_pdf === false) return true;
  if (f.research_readiness === "metadata_only") return true;
  if (!f.research_readiness && (f.size === 0 || !f.size)) return true;
  return false;
}

function attentionFor(f: UserFile): LibraryAttentionRow | null {
  if (f.kind !== "document") return null;
  if (f.meta_status === "failed") {
    return {
      file: f,
      kind: "failed",
      label: "Import failed",
      actionLabel: "Retry",
    };
  }
  if (f.meta_status === "pending" || f.meta_status === "running") {
    return {
      file: f,
      kind: "processing",
      label: "Processing",
      actionLabel: "View",
    };
  }
  if (isNeedsPdf(f)) {
    return {
      file: f,
      kind: "needs_pdf",
      label: "Needs PDF",
      actionLabel: "Attach PDF",
    };
  }
  return null;
}

/** Prefer in-progress reading, then unread with a PDF. */
export function pickContinuePaper(papers: UserFile[]): UserFile | null {
  const docs = papers.filter((f) => f.kind === "document");
  const reading = docs.find((f) => f.reading_status === "reading" && !isNeedsPdf(f));
  if (reading) return reading;
  const unread = docs.find(
    (f) =>
      (f.reading_status === "unread" || !f.reading_status) && !isNeedsPdf(f),
  );
  if (unread) return unread;
  return docs.find((f) => !isNeedsPdf(f)) ?? null;
}

export function buildLibraryListView(
  papers: UserFile[],
  opts?: { attentionLimit?: number },
): LibraryListView {
  const limit = opts?.attentionLimit ?? 3;
  const continuePaper = pickContinuePaper(papers);
  const attentionAll = papers
    .map(attentionFor)
    .filter((r): r is LibraryAttentionRow => r != null)
    // Don't also feature the continue paper as attention
    .filter((r) => r.file.id !== continuePaper?.id);

  return {
    continuePaper,
    attentionRows: attentionAll.slice(0, limit),
    attentionTotal: attentionAll.length,
  };
}

export function paperTitle(f: UserFile): string {
  return (f.title || f.name || "Untitled paper").trim();
}

export function paperAuthorsShort(f: UserFile): string | null {
  const a = f.authors?.split(";")[0]?.trim();
  return a || null;
}

export function readingStatusLabel(f: UserFile): string {
  const rs = f.reading_status ?? "unread";
  if (rs === "reading") return "Reading";
  if (rs === "read") return "Read";
  return "Unread";
}

/** One human status for a row — never Profile/Evidence/Chat chips. */
export function paperStatusLabel(f: UserFile): string {
  if (isNeedsPdf(f)) return "Needs PDF";
  if (f.meta_status === "failed") return "Import failed";
  if (f.meta_status === "pending" || f.meta_status === "running") return "Processing";
  return readingStatusLabel(f);
}
