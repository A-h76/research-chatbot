export interface Me {
  id: number;
  name: string;
  email: string;
  picture: string;
  custom_instructions: string;
  default_model: string;
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
    important_terms?: Record<string, string>;
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
