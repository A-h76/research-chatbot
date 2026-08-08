import type { SearchMode } from "@/types/api";

export type ResearchSkillId = "ask" | "synthesize" | "compare" | "extract" | "draft";

export const RESEARCH_SKILLS: {
  id: ResearchSkillId;
  label: string;
  description: string;
}[] = [
  { id: "ask", label: "Ask", description: "Answer grounded in scoped sources" },
  {
    id: "synthesize",
    label: "Synthesize",
    description: "Themes, agreements, and tensions",
  },
  {
    id: "compare",
    label: "Compare",
    description: "Methods, designs, samples, outcomes",
  },
  {
    id: "extract",
    label: "Extract",
    description: "PICO / methods / outcomes table",
  },
  {
    id: "draft",
    label: "Draft",
    description: "Citation-ready paragraph",
  },
];

export interface ChatSettings {
  model: string;
  searchMode: SearchMode;
  temperature: number | null;
  reasoningEffort: "low" | "medium" | "high" | null;
  memoryEnabled: boolean;
  skill: ResearchSkillId;
}

export interface PendingFile {
  id: number;
  name: string;
  kind: "image" | "document";
  uploading?: boolean;
  size?: number;
}

export interface SendPayload {
  conversation_id: number;
  message?: string;
  model: string;
  search: SearchMode;
  skill?: ResearchSkillId;
  /** Assistant Engine mode (ADR-0018) — optional; server classifies if omitted */
  assistant_mode?: string;
  attachments?: number[];
  regenerate?: boolean;
}

export interface CreateConversationInput {
  model: string;
  project_id?: number | null;
  file_id?: number | null;      // M7: paper chat
  temperature?: number | null;
  reasoning_effort?: "low" | "medium" | "high" | null;
  memory_enabled?: boolean;
}

export interface UpdateConversationInput {
  title?: string;
  model?: string;
  project_id?: number | null;
  temperature?: number | null;
  reasoning_effort?: "low" | "medium" | "high" | null;
  memory_enabled?: boolean;
}
