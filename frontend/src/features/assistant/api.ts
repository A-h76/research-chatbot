import { api } from "@/lib/apiClient";

export type AssistantAction = {
  id: string;
  label: string;
  href?: string;
  focus_composer?: boolean;
};

export type AssistantTurnResponse = {
  intent: string;
  intent_meta?: { label: string; title: string; detail?: string | null };
  mode: string;
  research_state: {
    user: { experience: string; goals: string[]; fields: string[]; display_name?: string };
    project: { id: number | null; title: string | null };
    corpus: {
      papers: number;
      evidence: number;
      themes: number;
      gaps: number;
      contradictions: number;
      coverage: number | null;
    };
    workflow: {
      stage: string;
      label: string;
      completion: { done: number; total: number };
      nextAction: { id: string; label: string; href: string; estimate?: string | null };
      blockers: string[];
      stages?: { id: string; label: string; status: string }[];
    };
    writing: { hasManuscript: boolean };
  };
  outcome: "local_reply" | "ask_profile" | "start_job" | string;
  local_reply?: {
    lines: string[];
    action_card?: { title: string; actions: AssistantAction[] } | null;
    profile_questions?: {
      id: string;
      prompt: string;
      options: { id: string; label: string }[];
    }[];
  };
  start_job?: { kind: string; message: string; mode: string; skill: string };
};

/** Shared Assistant Engine client — Home, Chat, Paper, Writing (ADR-0018). */
export const assistantApi = {
  session: (projectId?: number | null) =>
    api.get<AssistantTurnResponse>(
      `/api/assistant/session${projectId != null ? `?project_id=${projectId}` : ""}`,
    ),
  researchState: (projectId?: number | null) =>
    api.get<AssistantTurnResponse["research_state"]>(
      `/api/assistant/research-state${projectId != null ? `?project_id=${projectId}` : ""}`,
    ),
  turn: (body: {
    message: string;
    project_id?: number | null;
    surface?: string;
    conversation_id?: number | null;
  }) => api.post<AssistantTurnResponse>("/api/assistant/turn", body),
};

/**
 * Resolve mode for /api/chat. Prefer Engine; fall back silently on failure
 * so chat still works if assistant routes are down.
 */
export async function resolveAssistantMode(opts: {
  message: string;
  projectId?: number | null;
  surface: string;
  conversationId?: number | null;
}): Promise<string | undefined> {
  try {
    const decision = await assistantApi.turn({
      message: opts.message,
      project_id: opts.projectId,
      surface: opts.surface,
      conversation_id: opts.conversationId,
    });
    return decision.start_job?.mode || decision.mode || undefined;
  } catch {
    return undefined;
  }
}
