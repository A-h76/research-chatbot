/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from "vitest";
import { persistGroundedBindings } from "./GroundedDraftVerify";
import type { GroundedWritingResult } from "@/features/evidence/hooks/useGroundedWriting";

describe("persistGroundedBindings", () => {
  it("saves unique section bindings", async () => {
    const createBinding = vi.fn().mockResolvedValue({});
    const writing = {
      status: "ok",
      blocked_reason: null,
      mode: "grounded_v0",
      paragraph: "x",
      citations: [],
      warnings: [],
      disclaimer: "",
      sections: [
        {
          id: "themes",
          title: "Themes",
          paragraph: "Claim [#1].",
          citations: [],
          evidence_ids: [1],
          bindings: [
            { evidence_id: 1, claim: "A", quote: "q", page: 2 },
            { evidence_id: 1, claim: "A", quote: "q", page: 2 },
          ],
          confidence: "high",
          status: "ok",
        },
        {
          id: "key_findings",
          title: "Findings",
          paragraph: "More [#2].",
          citations: [],
          evidence_ids: [2],
          bindings: [{ evidence_id: 2, claim: "B", quote: "r", page: 3 }],
          confidence: "high",
          status: "ok",
        },
      ],
    } as GroundedWritingResult;

    const result = await persistGroundedBindings({
      documentId: 55,
      writing,
      createBinding,
    });

    expect(result.saved).toBe(2);
    expect(result.failed).toBe(0);
    expect(createBinding).toHaveBeenCalledTimes(2);
    expect(createBinding).toHaveBeenCalledWith(
      55,
      expect.objectContaining({
        evidence_object_id: 1,
        block_id: "writing_themes",
        relation: "supports",
      }),
    );
  });
});
