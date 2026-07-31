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

/** RI-002 matrix cell — cites evidence or marks unknown. */
export interface MatrixCell {
  value: string | null;
  status: "known" | "unknown" | "partial";
  evidence_ids: number[];
  sources: string[];
}

export interface MatrixRow {
  file_id: number;
  paper_title: string;
  paper_year: string;
  paper_authors: string;
  evidence_count: number;
  method: MatrixCell;
  dataset: MatrixCell;
  findings: MatrixCell;
  limitations: MatrixCell;
}

export interface EvidenceMatrixResponse {
  stage: "matrix";
  matrix_version: string;
  project_id: number;
  columns: string[];
  rows: MatrixRow[];
  metrics: {
    paper_count: number;
    cell_known: number;
    cell_unknown: number;
    coverage: number | null;
    papers_with_evidence: number;
  };
}

/** RI-001 theme cluster. */
export interface ThemeCluster {
  id: string;
  letter: string;
  label: string;
  key_terms: string[];
  evidence_ids: number[];
  file_ids: number[];
  size: number;
  sample_claims: Array<{
    evidence_id: number;
    claim: string;
    file_id?: number | null;
    page?: number | null;
  }>;
  study_types: string[];
}

export interface EvidenceThemesResponse {
  stage: "themes";
  themes_version: string;
  project_id: number | null;
  run: {
    algorithm: string;
    params: Record<string, unknown>;
    input_hash: string;
    object_count: number;
    generated_at: string;
  };
  themes: ThemeCluster[];
  unassigned: {
    evidence_ids: number[];
    count: number;
    reason: string;
  };
  metrics: {
    theme_count: number;
    assigned_evidence: number;
    unassigned_evidence: number;
    coverage: number | null;
    file_count: number;
  };
}

/** RI-005 project graph. */
export interface ProjectGraphNode {
  id: string;
  type: "paper" | "evidence" | "theme";
  label: string;
  ref: Record<string, unknown>;
}

export interface ProjectGraphEdge {
  id: string;
  source: string;
  target: string;
  type: "from" | "in_theme" | "contradicts" | "related" | "supports";
  evidence_ids?: number[];
  mediators?: string[];
  unexplained?: boolean;
}

export interface EvidenceGraphResponse {
  stage: "graph";
  graph_version: string;
  project_id: number;
  run: {
    input_hash: string;
    generated_at: string;
    sources: string[];
    themes_version?: string;
  };
  nodes: ProjectGraphNode[];
  edges: ProjectGraphEdge[];
  metrics: {
    node_count: number;
    edge_count: number;
    paper_count: number;
    evidence_count: number;
    theme_count: number;
    contradicts_count: number;
  };
}

/** RI-006 research gap. */
export interface ResearchGap {
  id: string;
  type:
    | "thin_theme"
    | "missing_matrix_cell"
    | "weak_consensus"
    | "unexplained_conflict"
    | "coverage";
  statement: string;
  evidence_density: number;
  suggested_questions: string[];
  evidence_ids: number[];
  theme_id?: string;
  file_ids?: number[];
  matrix?: { file_id: number; column: string };
  conflict_link?: { a_id: number; b_id: number };
}

export interface EvidenceGapsResponse {
  stage: "gaps";
  gaps_version: string;
  project_id: number;
  run: {
    input_hash: string;
    generated_at: string;
    params: Record<string, unknown>;
    sources: string[];
  };
  gaps: ResearchGap[];
  metrics: {
    gap_count: number;
    by_type: Record<string, number>;
    mean_density: number | null;
    evidence_count: number;
    paper_count: number;
  };
}

/** RI-007 timeline. */
export interface TimelineEntry {
  year: number | null;
  file_ids: number[];
  evidence_ids: number[];
  theme_ids: string[];
  theme_labels: string[];
  study_types: string[];
  paper_count: number;
  evidence_count: number;
  sample_claims: Array<{
    evidence_id: number;
    file_id?: number | null;
    claim: string;
    theme_ids: string[];
  }>;
}

export interface EvidenceTimelineResponse {
  stage: "timeline";
  timeline_version: string;
  project_id: number;
  run: { input_hash: string; generated_at: string; sources: string[] };
  span: { start_year: number | null; end_year: number | null; year_count: number };
  entries: TimelineEntry[];
  undated: TimelineEntry | null;
  evolution: Array<{
    theme_id: string;
    label: string;
    first_year: number;
    last_year: number;
    years: number[];
  }>;
  metrics: {
    dated_evidence: number;
    undated_evidence: number;
    paper_count: number;
    theme_span_count: number;
  };
}

/** RI-008 methodology card. */
export interface MethodologyCard {
  id: string;
  kind: "study_design" | "dataset" | "variables" | "statistics" | "threats_to_validity" | string;
  title: string;
  advice: string;
  tone: "advisory";
  evidence_ids: number[];
  file_ids?: number[];
  anchors?: Record<string, unknown>;
}

export interface EvidenceMethodologyResponse {
  stage: "methodology";
  methodology_version: string;
  project_id: number;
  run: { input_hash: string; generated_at: string; sources: string[] };
  cards: MethodologyCard[];
  design_summary: {
    counts: Record<string, number>;
    evidence_ids_by_design: Record<string, number[]>;
  };
  metrics: {
    card_count: number;
    by_kind: Record<string, number>;
    design_variety: number;
    evidence_count: number;
  };
  disclaimer: string;
}

/** W5 structured extract cell. */
export interface ExtractCell {
  value: string | null;
  status: "known" | "unknown";
  sources: string[];
}

export interface StructuredExtractRow {
  file_id: number;
  paper_title: string;
  paper_year: string;
  status: string;
  population: ExtractCell;
  intervention: ExtractCell;
  comparator: ExtractCell;
  outcomes: ExtractCell;
  study_design: ExtractCell;
  methods: ExtractCell;
  key_findings: ExtractCell;
  has_medical_understanding: boolean;
  evidence_count: number;
}

export interface StructuredExtractResponse {
  stage: "structured_extract";
  extract_version: string;
  project_id: number | null;
  columns: string[];
  rows: StructuredExtractRow[];
  metrics: {
    paper_count: number;
    filled_rows: number;
    empty_rows: number;
    coverage: number;
  };
}
