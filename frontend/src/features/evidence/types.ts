export type ConfidenceBand = "low" | "moderate" | "high";
export type EvidenceStatus = "candidate" | "accepted" | "rejected" | "superseded";
export type Sufficiency = "sufficient" | "weak" | "insufficient";

export interface EvidenceObjectDTO {
  id: number;
  status: EvidenceStatus;
  confidence_band: ConfidenceBand;
  claim: string;
  quote: string;
  page: number | null;
  section: string;
  file_id: number;
  file_title?: string;
  relation: "supports" | "contradicts" | "related";
  study_type: string;
  study_quality: string;
  supports: string[];
  contradicts: string[];
  limitations: string[];
  provenance?: Record<string, unknown>;
}

export interface ExplainResponse {
  status: "ok";
  sufficiency: Sufficiency;
  sentence: {
    block_id: string;
    range_start?: number;
    range_end?: number;
    text: string;
  };
  evidence: EvidenceObjectDTO[];
  chain: Array<{ step: string; detail: string }>;
  warnings: string[];
}
