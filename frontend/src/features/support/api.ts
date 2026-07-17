import { api } from "@/lib/apiClient";

export type SupportCategory = "general" | "bug" | "feature" | "account";

export interface SupportInput {
  email: string;
  category: SupportCategory;
  subject: string;
  message: string;
}

export const supportApi = {
  submit: (body: SupportInput) =>
    api.post<{ ok: boolean; ticket: number }>("/api/support", body),
};
