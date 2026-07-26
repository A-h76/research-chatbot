export const queryKeys = {
  me: ["me"] as const,
  models: ["models"] as const,
  projects: ["projects"] as const,
  conversations: ["conversations"] as const,
  conversation: (id: number) => ["conversations", id] as const,
  files: ["files"] as const,
  file: (id: number) => ["files", id] as const,
  fileAnalysis: (id: number) => ["files", id, "analysis"] as const,
  /** Phase 1 pipeline document (GET …/pipeline). */
  pipeline: (fileId: number) => ["pipeline", fileId] as const,
  /** Single phase payload (GET …/phases/:phase). */
  pipelinePhase: (fileId: number, phase: string) => ["pipeline", fileId, "phase", phase] as const,
  /** Alias used by architecture §7.2 — LLM narrative, not Phase 1. */
  analysis: (fileId: number) => ["files", fileId, "analysis"] as const,
  citations: ["citations"] as const,
  memories: ["memories"] as const,
  notes: ["notes"] as const,
  note: (id: number) => ["notes", id] as const,
  comparison: (id: number) => ["analysis", "compare", id] as const,
  gaps:       (id: number) => ["analysis", "gaps",    id] as const,
  search: (q: string, kinds?: string[], projectId?: number | null) =>
            ["search", q, kinds ?? "all", projectId ?? null] as const,
  aiPrompts: ["ai", "prompts"] as const,
};
