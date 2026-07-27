import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/queryKeys";
import { projectsApi, type ProjectInput, type QuestionInput } from "./api";
import type { ProjectQuestionStatus, ProjectResearchPreset } from "@/types/api";

export function useProjects() {
  return useQuery({ queryKey: queryKeys.projects, queryFn: projectsApi.list });
}

export function useProject(id: number | null) {
  return useQuery({
    queryKey: id ? ["projects", id] : ["projects", "none"],
    queryFn:  () => projectsApi.get(id!),
    enabled:  id !== null,
  });
}

/** Single hub read model — Overview renders from this alone. */
export function useProjectHub(id: number | null) {
  return useQuery({
    queryKey: id ? queryKeys.projectHub(id) : ["projects", "hub", "none"],
    queryFn:  () => projectsApi.hub(id!),
    enabled:  id !== null,
  });
}

export function useProjectQuestions(
  projectId: number | null,
  enabled = true,
  status?: ProjectQuestionStatus,
) {
  return useQuery({
    queryKey: projectId
      ? ["projects", projectId, "questions", status ?? "all"]
      : ["projects", "questions", "none"],
    queryFn: () => projectsApi.listQuestions(projectId!, status),
    enabled: projectId !== null && enabled,
  });
}

export function useProjectInsights(projectId: number | null, enabled = true) {
  return useQuery({
    queryKey: projectId
      ? ["projects", projectId, "insights"]
      : ["projects", "insights", "none"],
    queryFn: () => projectsApi.listInsights(projectId!),
    enabled: projectId !== null && enabled,
  });
}

export function useProjectResearchHistory(projectId: number | null, enabled = true) {
  return useQuery({
    queryKey: projectId
      ? queryKeys.projectResearchHistory(projectId)
      : ["projects", "research", "none"],
    queryFn: () => projectsApi.listResearchHistory(projectId!),
    enabled: projectId !== null && enabled,
  });
}

export function useProjectResearch(
  projectId: number | null,
  researchId: number | null,
) {
  return useQuery({
    queryKey:
      projectId && researchId
        ? queryKeys.projectResearch(projectId, researchId)
        : ["projects", "research", "none"],
    queryFn: () => projectsApi.getResearch(projectId!, researchId!),
    enabled: projectId !== null && researchId !== null,
    refetchInterval: (query) =>
      query.state.data?.status === "running" ? 3000 : false,
  });
}

export function useRunProjectResearch(projectId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      preset?: ProjectResearchPreset | null;
      query?: string;
      file_ids?: number[] | null;
      force?: boolean;
    }) => projectsApi.runResearch(projectId, body),
    onSuccess: (result) => {
      qc.setQueryData(
        queryKeys.projectResearch(projectId, result.id),
        result,
      );
      void qc.invalidateQueries({ queryKey: queryKeys.projectHub(projectId) });
      void qc.invalidateQueries({ queryKey: ["projects", projectId, "insights"] });
      void qc.invalidateQueries({
        queryKey: queryKeys.projectResearchHistory(projectId),
      });
      void qc.invalidateQueries({
        queryKey: ["projects", projectId, "memory"],
      });
    },
  });
}

export function useProjectMemory(projectId: number | null, enabled = true) {
  return useQuery({
    queryKey: projectId
      ? ["projects", projectId, "memory"]
      : ["projects", "memory", "none"],
    queryFn: () => projectsApi.listMemory(projectId!),
    enabled: projectId !== null && enabled,
  });
}

export function usePatchProjectMemory(projectId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      memoryId,
      action,
    }: {
      memoryId: number;
      action: "pin" | "unpin" | "archive" | "restore";
    }) => projectsApi.patchMemory(projectId, memoryId, action),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["projects", projectId, "memory"] });
      void qc.invalidateQueries({ queryKey: queryKeys.projectHub(projectId) });
      void qc.invalidateQueries({ queryKey: queryKeys.memories });
    },
  });
}

export function useDeleteProjectMemory(projectId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (memoryId: number) =>
      projectsApi.deleteMemory(projectId, memoryId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["projects", projectId, "memory"] });
      void qc.invalidateQueries({ queryKey: queryKeys.projectHub(projectId) });
      void qc.invalidateQueries({ queryKey: queryKeys.memories });
    },
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProjectInput) => projectsApi.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.projects });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useUpdateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<ProjectInput> }) =>
      projectsApi.update(id, body),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: queryKeys.projects });
      qc.invalidateQueries({ queryKey: ["projects", id] });
      qc.invalidateQueries({ queryKey: queryKeys.projectHub(id) });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => projectsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.projects });
      qc.invalidateQueries({ queryKey: queryKeys.conversations });
      qc.invalidateQueries({ queryKey: queryKeys.memories });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

function invalidateQuestions(qc: ReturnType<typeof useQueryClient>, projectId: number) {
  qc.invalidateQueries({ queryKey: queryKeys.projectHub(projectId) });
  qc.invalidateQueries({ queryKey: ["projects", projectId, "questions"] });
}

export function useCreateQuestion(projectId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: QuestionInput) => projectsApi.createQuestion(projectId, body),
    onSuccess: () => invalidateQuestions(qc, projectId),
  });
}

export function useUpdateQuestion(projectId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      questionId,
      body,
    }: {
      questionId: number;
      body: Partial<QuestionInput>;
    }) => projectsApi.updateQuestion(projectId, questionId, body),
    onSuccess: () => invalidateQuestions(qc, projectId),
  });
}

export function useDeleteQuestion(projectId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (questionId: number) =>
      projectsApi.deleteQuestion(projectId, questionId),
    onSuccess: () => invalidateQuestions(qc, projectId),
  });
}
