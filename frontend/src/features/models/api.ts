import { api } from "@/lib/apiClient";
import type { ModelsResponse } from "@/types/api";

export const modelsApi = {
  list: (refresh?: boolean) => api.get<ModelsResponse>(`/api/models${refresh ? "?refresh=1" : ""}`),
};
