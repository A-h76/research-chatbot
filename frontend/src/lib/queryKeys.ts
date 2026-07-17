export const queryKeys = {
  me: ["me"] as const,
  models: ["models"] as const,
  projects: ["projects"] as const,
  conversations: ["conversations"] as const,
  conversation: (id: number) => ["conversations", id] as const,
  files: ["files"] as const,
  file: (id: number) => ["files", id] as const,
  fileAnalysis: (id: number) => ["files", id, "analysis"] as const,
  citations: ["citations"] as const,
  memories: ["memories"] as const,
  notes: ["notes"] as const,
  note: (id: number) => ["notes", id] as const,
  comparison: (id: number) => ["analysis", "compare", id] as const,
  gaps:       (id: number) => ["analysis", "gaps",    id] as const,
  search: (q: string, kinds?: string[], projectId?: number | null) =>
            ["search", q, kinds ?? "all", projectId ?? null] as const,
};
