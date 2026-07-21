import type { SearchMode } from "@/types/api";

export interface ChatSettings {
  model: string;
  searchMode: SearchMode;
  temperature: number | null;
  reasoningEffort: "low" | "medium" | "high" | null;
  memoryEnabled: boolean;
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
