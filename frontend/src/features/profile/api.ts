import { api } from "@/lib/apiClient";
import type { Me } from "@/types/api";

export const profileApi = {
  me: () => api.get<Me>("/api/me"),
  updateInstructions: (custom_instructions: string) =>
    api.patch<{ ok: boolean }>("/api/profile", { custom_instructions }),
};
