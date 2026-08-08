import { describe, expect, it } from "vitest";
import {
  buildLibraryListView,
  paperStatusLabel,
  pickContinuePaper,
  pickSpotlight,
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

describe("pickSpotlight", () => {
  it("uses Continue for in-progress reading", () => {
    const papers = [
      f({ id: 1, name: "A", reading_status: "unread" }),
      f({ id: 2, name: "B", reading_status: "reading" }),
    ];
    const spot = pickSpotlight(papers);
    expect(spot?.paper.id).toBe(2);
    expect(spot?.mode).toBe("continue");
    expect(spot?.ctaLabel).toBe("Continue");
  });

  it("uses Recommended for unread (not Continue)", () => {
    const papers = [f({ id: 1, name: "A", reading_status: "unread" })];
    const spot = pickSpotlight(papers, {
      workflowStage: "literature_review",
      workflowLabel: "Literature review",
    });
    expect(spot?.mode).toBe("recommended");
    expect(spot?.reason.toLowerCase()).toContain("literature");
    expect(spot?.ctaLabel).toBe("Open");
  });

  it("skips papers that need a PDF", () => {
    const papers = [
      f({ id: 1, name: "A", reading_status: "reading", has_pdf: false }),
      f({ id: 2, name: "B", reading_status: "unread", has_pdf: true }),
    ];
    expect(pickSpotlight(papers)?.paper.id).toBe(2);
  });
});

describe("pickContinuePaper", () => {
  it("prefers reading over unread", () => {
    const papers = [
      f({ id: 1, name: "A", reading_status: "unread" }),
      f({ id: 2, name: "B", reading_status: "reading" }),
    ];
    expect(pickContinuePaper(papers)?.id).toBe(2);
  });
});

describe("buildLibraryListView", () => {
  it("surfaces spotlight + attention without KPI dump", () => {
    const view = buildLibraryListView([
      f({ id: 1, name: "Reading me", reading_status: "reading" }),
      f({
        id: 2,
        name: "No PDF",
        has_pdf: false,
        research_readiness: "metadata_only",
      }),
      f({ id: 3, name: "Ok", reading_status: "read" }),
    ]);
    expect(view.spotlight?.paper.id).toBe(1);
    expect(view.spotlight?.mode).toBe("continue");
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
      paperStatusLabel(
        f({ id: 2, name: "y", has_pdf: false, research_readiness: "metadata_only" }),
      ),
    ).toBe("Needs PDF");
  });
});
