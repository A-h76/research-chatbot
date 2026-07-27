export interface Me {
  id: number;
  name: string;
  email: string;
  picture: string;
  custom_instructions: string;
  default_model: string;
  beta_mode?: boolean;
}

export interface ModelsResponse {
  models: string[];
  default: string;
}

export interface Project {
  id: number;
  name: string;
  emoji: string;
  description: string;
  instructions: string;
}

export interface ProjectDetail extends Project {
  created_at: string | null;
  stats: {
    papers: number;
    chats: number;
    memories: number;
    unread: number;
    reading: number;
    read: number;
  };
}

/** GET /api/projects/:id/hub — single read model for Project Workspace. */
export interface ProjectHubPaper {
  id: number;
  name: string;
  title: string;
  authors: string;
  year: string;
  reading_status: ReadingStatus;
  meta_status: "pending" | "running" | "done" | "failed";
  created_at: string | null;
}

export interface ProjectHubNote {
  id: number;
  title: string;
  content_preview: string;
  file_id: number | null;
  updated_at: string | null;
}

export interface ProjectHubInsight {
  id: number;
  kind: string;
  title: string;
  created_at: string | null;
}

export interface ProjectHubQuestion {
  id: number;
  project_id?: number;
  text: string;
  status: ProjectQuestionStatus;
  source?: ProjectQuestionSource;
  linked_insight_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export type ProjectQuestionStatus = "open" | "answered" | "parked";
export type ProjectQuestionSource = "manual" | "ai";

export interface ProjectQuestion extends ProjectHubQuestion {
  project_id: number;
  source: ProjectQuestionSource;
  linked_insight_id: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ProjectHubActivity {
  kind: string;
  id: number;
  title: string;
  at: string | null;
}

export interface ProjectHub {
  project: Project & { created_at: string | null };
  stats: {
    papers: number;
    chats: number;
    memories: number;
    notes: number;
    open_questions: number;
    insights: number;
    unread: number;
    reading: number;
    read: number;
  };
  recent_papers: ProjectHubPaper[];
  recent_notes: ProjectHubNote[];
  open_questions: ProjectHubQuestion[];
  recent_insights: ProjectHubInsight[];
  pipeline_summary: {
    done: number;
    running: number;
    pending: number;
    failed: number;
    partial: number;
  };
  unread_activity: ProjectHubActivity[];
}

/** Full insight row from GET /api/projects/:id/insights */
export interface ProjectInsight extends ProjectHubInsight {
  file_ids: number[];
  preview: string;
  model: string;
}

/** Sprint B — project research support citation */
export interface ResearchSupport {
  paper_id: number;
  title: string;
  section: string;
  snippet: string;
  citation: string;
}

export interface ResearchClaim {
  claim: string;
  support: ResearchSupport[];
}

export type ProjectResearchPreset =
  | "evidence"
  | "disagree"
  | "methodology"
  | "open_questions"
  | "compare"
  | "datasets";

export interface ProjectResearchResult {
  id: number;
  kind: "research";
  status: "running" | "done" | "failed" | "pending";
  preset: ProjectResearchPreset | null;
  query: string;
  file_ids: number[];
  skipped: { id: number; name?: string; reason: string }[];
  summary: string;
  answer: string;
  claims: ResearchClaim[];
  supporting_file_ids: number[];
  derived_analysis_id: number;
  incomplete?: boolean;
  estimated_cost_usd?: number | null;
  actual_cost_usd?: number | null;
  created_at: string | null;
}

export interface ProjectResearchHistoryItem {
  id: number;
  status: string;
  preset: string;
  query: string;
  label: string;
  summary: string;
  created_at: string | null;
}

export interface ConversationSummary {
  id: number;
  title: string;
  model: string;
  project_id: number | null;
  file_id: number | null;
}

export interface ConversationSettings {
  temperature: number | null;
  reasoning_effort: "low" | "medium" | "high" | null;
  memory_enabled: boolean;
}

export interface Attachment {
  id: number;
  name: string;
  mime: string;
  kind: "image" | "document";
}

export interface Source {
  title: string;
  url: string;
  snippet?: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  attachments: Attachment[];
}

export interface Conversation extends ConversationSummary, ConversationSettings {
  file_id: number | null;
  messages: Message[];
}

export interface UserFile {
  id: number;
  name: string;
  kind: "image" | "document";
  size: number;
  project_id: number | null;
  /** Present on GET /api/files/:id when the paper belongs to a project. */
  project?: { id: number; name: string; emoji: string } | null;
  conversation_id: number | null;
  chunks: number;
  title: string;
  authors: string;
  year: string;
  venue: string;
  doi: string;
  abstract: string;
  reading_status: "unread" | "reading" | "read";
  tags: string[];
  meta_status: "pending" | "running" | "done" | "failed";
  created_at: string | null;
  /** Scholarly provenance — extracted | crossref | openalex | user */
  metadata_source?: string;
  /** OpenAlex OA / landing URL for metadata-only Discover stubs */
  source_url?: string;
  doi_verified?: boolean;
  crossref_last_synced?: string | null;
}

export interface PaperAnalysis {
  file_id: number;
  status: "pending" | "running" | "done" | "failed" | "none";
  error: string;
  model: string;
  updated_at: string | null;
  data: {
    executive_summary?: string;
    abstract_explained?: string;
    research_objective?: string;
    problem_statement?: string;
    methodology?: string;
    dataset?: string | null;
    experiments?: string;
    results?: string;
    key_contributions?: string[];
    strengths?: string[];
    limitations?: string[];
    future_work?: string[];
    keywords?: string[];
    // Array of {term, definition} pairs, not a free-form dict — matches
    // backend/ai/prompts.py's PAPER_ANALYSIS_RESPONSE_FORMAT, whose strict
    // JSON Schema mode has no way to express an arbitrarily-keyed object.
    important_terms?: { term: string; definition: string }[];

    // Present only when domain="medical" — always these 3 (backend/ai/
    // prompts.py's MEDICAL_CORE_FIELDS), regardless of document_type.
    clinical_relevance?: string;
    clinical_translation?: string;
    clinical_bottom_line?: string;

    // domain="medical" + document_type="research" (MEDICAL_RESEARCH_FIELDS).
    pico_extraction?: string;
    evidence_quality?: string;
    risk_of_bias_assessment?: string;
    clinical_outcomes?: string;
    grade_assessment?: string;
    patient_population?: string;
    ethics_patient_consent?: string;

    // domain="medical" + document_type="clinical_guide" (MEDICAL_CLINICAL_GUIDE_FIELDS).
    target_audience?: string;
    scope_of_content?: string;
    practical_value?: string;
    evidence_base?: string;
    critical_assessment?: string;
    comparison_to_other_resources?: string;

    // domain="medical" + document_type="review" (MEDICAL_REVIEW_FIELDS).
    review_coverage?: string;
    search_strategy?: string;
    quality_of_included_studies?: string;
    key_findings?: string;
    gaps_in_literature?: string;
    future_research_directions?: string;
  };
}

// ── Citation (M13 — APA / IEEE / BibTeX) ────────────────────────────────────
export type CitationFormat = "bibtex" | "apa" | "ieee";

export interface Citation {
  id: number;
  authors: string;
  title: string;
  year: string;
  venue: string;
  doi: string;
  url: string;
  notes: string;
  project_id: number | null;
  // All three formats pre-formatted by the backend
  bibtex: string;
  apa: string;
  ieee: string;
  created_at: string | null;
}

export interface Memory {
  id: number;
  fact: string;
  project_id: number | null;
  importance: number;
  created_at: string;
  kind?: ProjectMemoryKind;
  source?: ProjectMemorySource;
  source_ref?: string;
  payload?: ProjectMemoryPayload;
  pinned?: boolean;
  status?: ProjectMemoryStatus;
  claim_hash?: string;
}

export type ProjectMemoryKind =
  | "finding"
  | "claim"
  | "contradiction"
  | "open_question"
  | "insight"
  | "fact";

export type ProjectMemorySource =
  | "research"
  | "compare"
  | "gaps"
  | "manual"
  | "chat";

export type ProjectMemoryStatus = "active" | "archived" | "deleted";

export interface ProjectMemoryPayload {
  paper_ids?: number[];
  claim?: string;
  citations?: {
    paper_id: number;
    title?: string;
    section?: string;
    snippet?: string;
    citation?: string;
  }[];
}

/** Project research memory row (Sprint C). */
export interface ProjectMemory {
  id: number;
  project_id: number | null;
  fact: string;
  kind: ProjectMemoryKind;
  source: ProjectMemorySource;
  source_ref: string;
  payload: ProjectMemoryPayload;
  pinned: boolean;
  status: ProjectMemoryStatus;
  importance: number;
  claim_hash: string;
  created_at: string | null;
}

export type SearchMode = "off" | "auto" | "on";
export type ReadingStatus = "unread" | "reading" | "read";

// ── Notes (M10) ──────────────────────────────────────────────────────────────
export interface Note {
  id: number;
  title: string;
  content: string;
  project_id: number | null;
  file_id: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface NoteListResponse {
  total: number;
  offset: number;
  limit: number;
  items: Note[];
}

// ── Multi-Paper Analysis (M11) ────────────────────────────────────────────────
export interface ComparisonData {
  overview?: string;
  similarities?: string[];
  differences?: string[];
  common_datasets?: string[];
  methodologies?: Record<string, string>;
  agreements?: string[];
  contradictions?: string[];
  research_trends?: string[];
  synthesis?: string;
  error?: string;
}

export interface ComparisonResult {
  id: number;
  kind: "compare";
  file_ids: number[];
  status: "running" | "done" | "pending";
  data: ComparisonData;
  model: string;
  created_at: string | null;
  skipped?: { id: number; name?: string; reason: string }[];
}

// ── Research Gap Finder (M12) ─────────────────────────────────────────────────
export interface GapFinderData {
  preamble?: string;
  underexplored_topics?: string[];
  missing_experiments?: string[];
  open_questions?: string[];
  methodological_gaps?: string[];
  dataset_gaps?: string[];
  potential_thesis_ideas?: string[];
  future_opportunities?: string[];
  disclaimer?: string;
  error?: string;
}

export interface GapFinderResult {
  id: number;
  kind: "gaps";
  file_ids: number[];
  status: "running" | "done" | "pending";
  data: GapFinderData;
  model: string;
  created_at: string | null;
  skipped?: { id: number; name?: string; reason: string }[];
}

// ── Semantic Search (M14) ────────────────────────────────────────────────────
export interface SearchResult {
  kind: "paper" | "note" | "citation" | "chat";
  ref_id: number;
  chunk_id?: number;
  title: string;
  snippet: string;
  score: number;
  url: string;
  page: number | null;
  section: string | null;
  file_name: string | null;
}

export interface SearchResponse {
  q: string;
  total: number;
  results: SearchResult[];
}

// ── AI Writing Assistant (M15) ────────────────────────────────────────────────
export type WritingAction =
  | "rewrite_academic"
  | "improve_grammar"
  | "improve_clarity"
  | "expand"
  | "shorten"
  | "generate_abstract"
  | "improve_conclusion";

export interface WritingResponse {
  result: string;
  action: WritingAction;
  warning: string;
}

// ── AI layer (backend/ai) ─────────────────────────────────────────────────────
export interface AiPrompt {
  name: string;
  version: number;
  template: string;
  is_active: boolean;
  created_at: string | null;
}

export interface AiPromptsResponse {
  prompts: AiPrompt[];
}

export interface AiTestResult {
  content: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  finish_reason: string;
  cost: number;
}
