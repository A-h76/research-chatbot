import type { ExplainResponse, EvidenceObjectDTO, Sufficiency } from "../types";

/** Preserve API order — never re-rank client-side (ADD / FE TDS). */
export function mapExplainResponse(raw: ExplainResponse): ExplainResponse {
  return {
    status: "ok",
    sufficiency: (raw.sufficiency || "insufficient") as Sufficiency,
    sentence: {
      block_id: raw.sentence?.block_id || "",
      range_start: raw.sentence?.range_start,
      range_end: raw.sentence?.range_end,
      text: raw.sentence?.text || "",
    },
    evidence: Array.isArray(raw.evidence) ? raw.evidence.map(mapEvidenceObject) : [],
    chain: Array.isArray(raw.chain) ? raw.chain : [],
    warnings: Array.isArray(raw.warnings) ? raw.warnings : [],
  };
}

export function mapEvidenceObject(raw: EvidenceObjectDTO): EvidenceObjectDTO {
  return {
    id: Number(raw.id),
    status: raw.status,
    confidence_band: raw.confidence_band,
    claim: raw.claim || "",
    quote: raw.quote || "",
    page: raw.page ?? null,
    section: raw.section || "",
    file_id: Number(raw.file_id),
    file_title: raw.file_title,
    relation: raw.relation || "supports",
    study_type: raw.study_type || "",
    study_quality: raw.study_quality || "",
    supports: raw.supports || [],
    contradicts: raw.contradicts || [],
    limitations: raw.limitations || [],
    provenance: raw.provenance,
  };
}
