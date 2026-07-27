import { api } from "@/lib/apiClient";
import type {
  Project,
  ProjectDetail,
  ProjectHub,
  ProjectInsight,
  ProjectMemory,
  ProjectMemoryKind,
  ProjectMemorySource,
  ProjectQuestion,
  ProjectQuestionStatus,
  ProjectResearchHistoryItem,
  ProjectResearchPreset,
  ProjectResearchResult,
} from "@/types/api";

export interface ProjectInput {
  name: string;
  emoji: string;
  description: string;
  instructions: string;
}

export interface QuestionInput {
  text: string;
  status?: ProjectQuestionStatus;
  source?: "manual" | "ai";
}

export const projectsApi = {
  list:   () => api.get<Project[]>("/api/projects"),
  get:    (id: number) => api.get<ProjectDetail>(`/api/projects/${id}`),
  /** Single read model for Project Workspace — Overview must not fan out. */
  hub:    (id: number) => api.get<ProjectHub>(`/api/projects/${id}/hub`),
  create: (body: ProjectInput) => api.post<Project>("/api/projects", body),
  update: (id: number, body: Partial<ProjectInput>) =>
    api.patch<Project>(`/api/projects/${id}`, body),
  remove: (id: number) => api.delete<{ ok: boolean }>(`/api/projects/${id}`),

  listQuestions: (projectId: number, status?: ProjectQuestionStatus) => {
    const qs = status ? `?status=${status}` : "";
    return api.get<{ items: ProjectQuestion[]; total: number }>(
      `/api/projects/${projectId}/questions${qs}`,
    );
  },
  createQuestion: (projectId: number, body: QuestionInput) =>
    api.post<ProjectQuestion>(`/api/projects/${projectId}/questions`, body),
  updateQuestion: (
    projectId: number,
    questionId: number,
    body: Partial<QuestionInput>,
  ) =>
    api.patch<ProjectQuestion>(
      `/api/projects/${projectId}/questions/${questionId}`,
      body,
    ),
  deleteQuestion: (projectId: number, questionId: number) =>
    api.delete<{ ok: boolean }>(
      `/api/projects/${projectId}/questions/${questionId}`,
    ),

  listInsights: (projectId: number) =>
    api.get<{ items: ProjectInsight[]; total: number }>(
      `/api/projects/${projectId}/insights`,
    ),

  listResearchHistory: (projectId: number) =>
    api.get<{ items: ProjectResearchHistoryItem[]; total: number }>(
      `/api/projects/${projectId}/research`,
    ),

  runResearch: (
    projectId: number,
    body: {
      preset?: ProjectResearchPreset | null;
      query?: string;
      file_ids?: number[] | null;
      force?: boolean;
    },
  ) => api.post<ProjectResearchResult>(`/api/projects/${projectId}/research`, body),

  getResearch: (projectId: number, researchId: number) =>
    api.get<ProjectResearchResult>(
      `/api/projects/${projectId}/research/${researchId}`,
    ),

  listMemory: (
    projectId: number,
    params?: { kind?: ProjectMemoryKind; source?: ProjectMemorySource; pinned?: boolean },
  ) => {
    const qs = new URLSearchParams();
    if (params?.kind) qs.set("kind", params.kind);
    if (params?.source) qs.set("source", params.source);
    if (params?.pinned != null) qs.set("pinned", params.pinned ? "1" : "0");
    const q = qs.toString();
    return api.get<{ items: ProjectMemory[]; total: number }>(
      `/api/projects/${projectId}/memory${q ? `?${q}` : ""}`,
    );
  },

  patchMemory: (
    projectId: number,
    memoryId: number,
    action: "pin" | "unpin" | "archive" | "restore",
  ) =>
    api.patch<ProjectMemory>(`/api/projects/${projectId}/memory/${memoryId}`, {
      action,
    }),

  deleteMemory: (projectId: number, memoryId: number) =>
    api.delete<{ ok: boolean }>(`/api/projects/${projectId}/memory/${memoryId}`),
};
