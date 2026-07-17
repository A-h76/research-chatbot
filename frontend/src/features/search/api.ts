import { api } from "@/lib/apiClient";
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
