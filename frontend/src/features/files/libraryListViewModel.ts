/**
 * Library list view model — Constitution: Invisible Intelligence.
 * Answers: "Which paper should I read next?"
 * Spotlight (Continue | Recommended) · calm list. No KPI dump.
 */

import type { UserFile } from "@/types/api";

export type LibraryAttentionKind = "needs_pdf" | "failed" | "processing";

export type LibraryAttentionRow = {
  file: UserFile;
  kind: LibraryAttentionKind;
  label: string;
  actionLabel: string;
};

export type LibrarySpotlightMode = "continue" | "recommended";

export type LibrarySpotlight = {
  paper: UserFile;
  mode: LibrarySpotlightMode;
  /** Short workflow reason — not AI fluff. */
  reason: string;
  ctaLabel: string;
};

export type LibraryListView = {
  spotlight: LibrarySpotlight | null;
  /** @deprecated use spotlight — kept for gradual migration */
  continuePaper: UserFile | null;
  attentionRows: LibraryAttentionRow[];
  attentionTotal: number;
};

export function isNeedsPdf(f: UserFile): boolean {
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

export type LibrarySpotlightContext = {
  /** Research State workflow stage id, if known */
  workflowStage?: string | null;
  workflowLabel?: string | null;
};

function recommendedReason(ctx?: LibrarySpotlightContext): string {
  const stage = (ctx?.workflowStage ?? "").toLowerCase();
  const label = (ctx?.workflowLabel ?? "").toLowerCase();
  if (
    stage.includes("writ") ||
    label.includes("writ") ||
    stage.includes("manuscript")
  ) {
    return "Read this next — it supports your current writing.";
  }
  if (
    stage.includes("evidence") ||
    label.includes("evidence") ||
    stage.includes("extract")
  ) {
    return "Read this next — it can feed evidence for your review.";
  }
  if (
    stage.includes("literat") ||
    stage.includes("library") ||
    label.includes("literat") ||
    label.includes("review")
  ) {
    return "Read this next — it supports your current literature review.";
  }
  return "Read this next for your active research.";
}

/** Prefer in-progress reading (Continue); else unread with PDF (Recommended). */
export function pickSpotlight(
  papers: UserFile[],
  ctx?: LibrarySpotlightContext,
): LibrarySpotlight | null {
  const docs = papers.filter((f) => f.kind === "document");
  const reading = docs.find(
    (f) => f.reading_status === "reading" && !isNeedsPdf(f),
  );
  if (reading) {
    return {
      paper: reading,
      mode: "continue",
      reason: "Pick up where you left off.",
      ctaLabel: "Continue",
    };
  }
  const unread = docs.find(
    (f) =>
      (f.reading_status === "unread" || !f.reading_status) && !isNeedsPdf(f),
  );
  if (unread) {
    return {
      paper: unread,
      mode: "recommended",
      reason: recommendedReason(ctx),
      ctaLabel: "Open",
    };
  }
  const any = docs.find((f) => !isNeedsPdf(f));
  if (!any) return null;
  if (any.reading_status === "read") {
    return {
      paper: any,
      mode: "recommended",
      reason: "Revisit this paper for your active research.",
      ctaLabel: "Open",
    };
  }
  return {
    paper: any,
    mode: "recommended",
    reason: recommendedReason(ctx),
    ctaLabel: "Open",
  };
}

/** @deprecated prefer pickSpotlight */
export function pickContinuePaper(papers: UserFile[]): UserFile | null {
  return pickSpotlight(papers)?.paper ?? null;
}

export function buildLibraryListView(
  papers: UserFile[],
  opts?: { attentionLimit?: number; spotlightContext?: LibrarySpotlightContext },
): LibraryListView {
  const limit = opts?.attentionLimit ?? 3;
  const spotlight = pickSpotlight(papers, opts?.spotlightContext);
  const attentionAll = papers
    .map(attentionFor)
    .filter((r): r is LibraryAttentionRow => r != null)
    .filter((r) => r.file.id !== spotlight?.paper.id);

  return {
    spotlight,
    continuePaper: spotlight?.paper ?? null,
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

/** Compact “why it’s here” line: Author · Year */
export function paperContextLine(f: UserFile): string | null {
  const authors = paperAuthorsShort(f);
  const year = f.year?.trim() || null;
  const parts = [authors, year].filter(Boolean);
  return parts.length ? parts.join(" · ") : null;
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
