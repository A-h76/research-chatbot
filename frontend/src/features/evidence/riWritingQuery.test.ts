import { describe, expect, it } from "vitest";

/**
 * Smoke: Evidence Query shape used by grounded writing / reason hooks.
 * Keeps RI productization entry fields stable.
 */
function buildWritingQuery(opts: {
  projectId: number;
  documentId: number;
  selectedText: string;
  sectionType?: string;
}) {
  const focus = opts.selectedText.trim().slice(0, 2000);
  return {
    intent: "support_sentence",
    section_type: opts.sectionType || "support_sentence",
    scope: { project_id: opts.projectId, document_id: opts.documentId },
    filters: { status: ["accepted", "candidate"], require_page_anchor: true },
    ranking_strategy: "default_v0",
    result_limit: 20,
    query_text: focus,
    anchors: { selected_text: focus },
  };
}

describe("RI Writing productization query shape", () => {
  it("builds support_sentence EvidenceQuery without model knobs", () => {
    const q = buildWritingQuery({
      projectId: 2,
      documentId: 55,
      selectedText: "Drug X reduces HbA1c",
    });
    expect(q.intent).toBe("support_sentence");
    expect(q.section_type).toBe("support_sentence");
    expect(q.scope.project_id).toBe(2);
    expect(q.ranking_strategy).toBe("default_v0");
    expect(q).not.toHaveProperty("model");
    expect(q).not.toHaveProperty("prompt");
    expect(q).not.toHaveProperty("embeddings");
  });

  it("passes section_type for Milestone 1 section drafts", () => {
    const q = buildWritingQuery({
      projectId: 2,
      documentId: 55,
      selectedText: "Drug X",
      sectionType: "literature_review",
    });
    expect(q.section_type).toBe("literature_review");
  });
});
