import { api } from "@/lib/apiClient";
import type { Project, ProjectDetail } from "@/types/api";

export interface ProjectInput {
  name: string;
  emoji: string;
  description: string;
  instructions: string;
}

export const projectsApi = {
  list:   () => api.get<Project[]>("/api/projects"),
  get:    (id: number) => api.get<ProjectDetail>(`/api/projects/${id}`),
  create: (body: ProjectInput) => api.post<Project>("/api/projects", body),
  update: (id: number, body: Partial<ProjectInput>) =>
    api.patch<Project>(`/api/projects/${id}`, body),
  remove: (id: number) => api.delete<{ ok: boolean }>(`/api/projects/${id}`),
};
