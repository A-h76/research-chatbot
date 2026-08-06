import type { PaperAnalysis, UserFile } from "@/types/api";

export type NoteSuggestionSection =
  | "Summary"
  | "Contribution"
  | "Limitation"
  | "Strength"
  | "Methodology"
  | "Results"
  | "Key term";

export interface NoteSuggestion {
  /** Stable id for dismiss / dedupe */
  id: string;
  fileId: number;
  paperTitle: string;
  section: NoteSuggestionSection;
  title: string;
  content: string;
  excerpt: string;
}

const MAX_EXCERPT = 320;
const MAX_PER_PAPER = 4;
const MAX_TOTAL = 16;

function clip(text: string, max = MAX_EXCERPT): string {
  const t = text.trim();
  if (t.length <= max) return t;
  return t.slice(0, max).trimEnd() + "…";
}

function suggestionId(fileId: number, section: string, body: string): string {
  const slug = body.slice(0, 48).replace(/\s+/g, " ").trim();
  return `${fileId}:${section}:${slug}`;
}

function paperLabel(file: UserFile): string {
  return file.title?.trim() || file.name;
}

function attribution(file: UserFile): string {
  const bits = [paperLabel(file)];
  const author = file.authors?.split(";")[0]?.trim();
  if (author) bits.push(author);
  if (file.year) bits.push(file.year);
  return bits.join(" · ");
}

function pushSuggestion(
  out: NoteSuggestion[],
  file: UserFile,
  section: NoteSuggestionSection,
  body: string,
  titleSuffix: string,
) {
  const excerpt = clip(body);
  if (!excerpt) return;
  out.push({
    id: suggestionId(file.id, section, excerpt),
    fileId: file.id,
    paperTitle: paperLabel(file),
    section,
    title: `${titleSuffix} · ${paperLabel(file)}`.slice(0, 120),
    content: `${excerpt}\n\n— ${attribution(file)}`,
    excerpt,
  });
}

/** Extract note-worthy passages from structured paper analysis (client-side). */
export function extractNoteSuggestions(
  file: UserFile,
  analysis: PaperAnalysis | null | undefined,
): NoteSuggestion[] {
  if (!analysis || analysis.status !== "done" || !analysis.data) return [];

  const data = analysis.data;
  const out: NoteSuggestion[] = [];

  if (data.executive_summary?.trim()) {
    pushSuggestion(out, file, "Summary", data.executive_summary, "Summary");
  }

  for (const item of data.key_contributions ?? []) {
    if (typeof item === "string" && item.trim()) {
      pushSuggestion(out, file, "Contribution", item, "Contribution");
    }
  }

  for (const item of data.limitations ?? []) {
    if (typeof item === "string" && item.trim()) {
      pushSuggestion(out, file, "Limitation", item, "Limitation");
    }
  }

  for (const item of data.strengths ?? []) {
    if (typeof item === "string" && item.trim()) {
      pushSuggestion(out, file, "Strength", item, "Strength");
    }
  }

  if (data.methodology?.trim()) {
    pushSuggestion(out, file, "Methodology", data.methodology, "Methodology");
  }

  if (data.results?.trim()) {
    pushSuggestion(out, file, "Results", data.results, "Results");
  }

  for (const term of data.important_terms ?? []) {
    const text = term?.definition?.trim()
      ? `${term.term}: ${term.definition}`
      : term?.term?.trim() ?? "";
    if (text) {
      pushSuggestion(out, file, "Key term", text, term.term || "Key term");
    }
  }

  return out.slice(0, MAX_PER_PAPER);
}

export function collectProjectNoteSuggestions(
  files: UserFile[],
  analysesByFileId: Map<number, PaperAnalysis | null>,
): NoteSuggestion[] {
  const all: NoteSuggestion[] = [];
  for (const file of files) {
    const suggestions = extractNoteSuggestions(file, analysesByFileId.get(file.id) ?? null);
    all.push(...suggestions);
  }
  return all.slice(0, MAX_TOTAL);
}

/** Hide suggestions already captured in user notes (simple excerpt match). */
export function filterSavedNoteSuggestions(
  suggestions: NoteSuggestion[],
  notes: { content: string }[],
): NoteSuggestion[] {
  if (notes.length === 0) return suggestions;
  const normalizedNotes = notes.map((n) => n.content.trim().toLowerCase()).filter(Boolean);
  return suggestions.filter((s) => {
    const needle = s.excerpt.trim().toLowerCase().slice(0, 80);
    if (!needle) return true;
    return !normalizedNotes.some((n) => n.includes(needle) || needle.includes(n.slice(0, 80)));
  });
}

export { MAX_TOTAL as MAX_NOTE_SUGGESTIONS };
