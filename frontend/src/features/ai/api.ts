import { api } from "@/lib/apiClient";
import type { AiPromptsResponse, AiTestResult } from "@/types/api";

export interface AiTestInput {
  model?: string;
  message?: string;
  max_tokens?: number;
}

export const aiApi = {
  listPrompts: () => api.get<AiPromptsResponse>("/api/ai/prompts"),
  test: (body: AiTestInput = {}) => api.post<AiTestResult>("/api/ai/test", body),
};
