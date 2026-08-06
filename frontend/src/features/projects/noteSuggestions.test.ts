import { describe, expect, it } from "vitest";
import type { PaperAnalysis, UserFile } from "@/types/api";
import {
  extractNoteSuggestions,
  filterSavedNoteSuggestions,
} from "./noteSuggestions";

function file(overrides: Partial<UserFile> = {}): UserFile {
  return {
    id: 1,
    name: "paper.pdf",
    kind: "document",
    size: 1,
    project_id: 1,
    conversation_id: null,
    chunks: 1,
    title: "AI in Healthcare",
    authors: "Smith, J.",
    year: "2024",
    venue: "",
    doi: "",
    abstract: "",
    reading_status: "unread",
    tags: [],
    meta_status: "done",
    created_at: null,
    paper_analysis_status: "done",
    cross_paper_research_ready: true,
    ...overrides,
  };
}

const analysis: PaperAnalysis = {
  file_id: 1,
  status: "done",
  error: "",
  model: "gpt-4o-mini",
  updated_at: null,
  data: {
    executive_summary: "This paper reviews AI diagnostics in hospitals.",
    key_contributions: ["Novel triage model", "Open benchmark"],
    limitations: ["Single-site evaluation"],
    methodology: "Retrospective cohort with 10k patients.",
  },
};

describe("noteSuggestions", () => {
  it("extracts structured analysis fields as suggestions", () => {
    const items = extractNoteSuggestions(file(), analysis);
    expect(items.length).toBeGreaterThanOrEqual(4);
    expect(items.some((s) => s.section === "Summary")).toBe(true);
    expect(items.some((s) => s.excerpt.includes("triage model"))).toBe(true);
    expect(items.every((s) => s.fileId === 1)).toBe(true);
  });

  it("returns empty when analysis is not done", () => {
    expect(extractNoteSuggestions(file(), { ...analysis, status: "pending" })).toEqual([]);
  });

  it("filters suggestions already present in notes", () => {
    const items = extractNoteSuggestions(file(), analysis);
    const filtered = filterSavedNoteSuggestions(items, [
      { content: "Novel triage model\n\n— AI in Healthcare" },
    ]);
    expect(filtered.some((s) => s.excerpt.includes("triage model"))).toBe(false);
    expect(filtered.length).toBeLessThan(items.length);
  });
});
