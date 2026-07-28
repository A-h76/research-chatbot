import { describe, expect, it } from "vitest";
import { mapExplainResponse } from "./evidenceMappers";
import type { ExplainResponse } from "../types";

const sufficient = {
  status: "ok",
  sufficiency: "sufficient",
  sentence: { block_id: "blk_1", text: "Sentence one." },
  evidence: [
    {
      id: 901,
      status: "accepted",
      confidence_band: "high",
      claim: "Drug X reduces outcome Y",
      quote: "significant reduction",
      page: 2,
      section: "Results",
      file_id: 10,
      file_title: "Paper A",
      relation: "supports",
      study_type: "RCT",
      study_quality: "high",
      supports: [],
      contradicts: [],
      limitations: [],
    },
  ],
  chain: [{ step: "binding", detail: "anchor blk_1 → evidence 901 (supports)" }],
  warnings: [],
} as ExplainResponse;

const insufficient = {
  status: "ok",
  sufficiency: "insufficient",
  sentence: { block_id: "blk_missing", text: "Unsupported claim." },
  evidence: [],
  chain: [],
  warnings: [],
} as ExplainResponse;

describe("evidenceMappers", () => {
  it("preserves API evidence order", () => {
    const mapped = mapExplainResponse(sufficient);
    expect(mapped.sufficiency).toBe("sufficient");
    expect(mapped.evidence.map((e) => e.id)).toEqual([901]);
  });

  it("maps insufficient empty evidence", () => {
    const mapped = mapExplainResponse(insufficient);
    expect(mapped.sufficiency).toBe("insufficient");
    expect(mapped.evidence).toEqual([]);
  });
});
