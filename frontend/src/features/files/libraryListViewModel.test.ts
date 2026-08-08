import { describe, expect, it } from "vitest";
import {
  buildLibraryListView,
  paperStatusLabel,
  pickContinuePaper,
} from "./libraryListViewModel";
import type { UserFile } from "@/types/api";

const f = (partial: Partial<UserFile> & { id: number; name: string }): UserFile =>
  ({
    kind: "document",
    title: partial.title ?? partial.name,
    authors: "",
    year: "",
    venue: "",
    reading_status: "unread",
    tags: [],
    meta_status: "done",
    created_at: null,
    size: 1024,
    has_pdf: true,
    ...partial,
  }) as UserFile;

describe("pickContinuePaper", () => {
  it("prefers reading over unread", () => {
    const papers = [
      f({ id: 1, name: "A", reading_status: "unread" }),
      f({ id: 2, name: "B", reading_status: "reading" }),
    ];
    expect(pickContinuePaper(papers)?.id).toBe(2);
  });

  it("skips papers that need a PDF", () => {
    const papers = [
      f({ id: 1, name: "A", reading_status: "reading", has_pdf: false }),
      f({ id: 2, name: "B", reading_status: "unread", has_pdf: true }),
    ];
    expect(pickContinuePaper(papers)?.id).toBe(2);
  });
});

describe("buildLibraryListView", () => {
  it("surfaces continue + attention without KPI dump", () => {
    const view = buildLibraryListView([
      f({ id: 1, name: "Reading me", reading_status: "reading" }),
      f({ id: 2, name: "No PDF", has_pdf: false, research_readiness: "metadata_only" }),
      f({ id: 3, name: "Ok", reading_status: "read" }),
    ]);
    expect(view.continuePaper?.id).toBe(1);
    expect(view.attentionRows).toHaveLength(1);
    expect(view.attentionRows[0].kind).toBe("needs_pdf");
    expect(view.attentionTotal).toBe(1);
  });
});

describe("paperStatusLabel", () => {
  it("uses one human status", () => {
    expect(paperStatusLabel(f({ id: 1, name: "x", reading_status: "reading" }))).toBe(
      "Reading",
    );
    expect(
      paperStatusLabel(f({ id: 2, name: "y", has_pdf: false, research_readiness: "metadata_only" })),
    ).toBe("Needs PDF");
  });
});
