import { api, getBearerToken } from "@/lib/apiClient";
import type { SearchResponse } from "@/types/api";

export interface SearchInput {
  q: string;
  kinds?: ("paper" | "note" | "citation" | "chat")[];
  project_id?: number | null;
  limit?: number;
}

export const searchApi = {
  search: (body: SearchInput) =>
    api.post<SearchResponse>("/api/search", body),
};

// ── Ask AI (RAG) ── JWT-only, documents only — see backend/search/routes.py
export interface RagInput {
  query: string;
  file_id?: number | null;
  project_id?: number | null;
  top_k?: number;
}

export interface RagSource {
  document_id: number;
  chunk_id: number;
  title: string;
  score: number;
  page: number | null;
  section: string | null;
}

export interface RagAnswer {
  answer: string | null;
  model?: string;
  sources: RagSource[];
  message?: string;
}

export const ragApi = {
  ask: async (body: RagInput): Promise<RagAnswer> => {
    const token = await getBearerToken();
    return api.post<RagAnswer>("/api/rag", body, token);
  },
};
