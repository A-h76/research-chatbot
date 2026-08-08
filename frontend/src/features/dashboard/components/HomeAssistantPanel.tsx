/**
 * Home Research Mentor UI — renders Assistant Engine decisions (ADR-0018).
 * Frontend looks; backend thinks.
 */
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ArrowUp, Check, Loader2, Square } from "lucide-react";
import { useUI } from "@/context/UIContext";
import { useMe } from "@/features/profile/useMe";
import {
  useConversation,
  useCreateConversation,
} from "@/features/chat/hooks/useConversation";
import { useChatStream } from "@/features/chat/hooks/useChatStream";
import { appendUserMessage } from "@/features/chat/lib/optimistic";
import { api } from "@/lib/apiClient";
import { cn } from "@/lib/utils";
import {
  MENTOR_EXPERIENCE,
  MENTOR_FIELDS,
  MENTOR_GOALS,
  MENTOR_ROLES,
} from "../mentorProfile";
import {
  assistantApi,
  type AssistantAction,
  type AssistantTurnResponse,
} from "../assistantApi";

const STORAGE_KEY = "dhund:home-assistant-conversation";

type LocalTurn =
  | {
      id: string;
      role: "user";
      text: string;
      meta?: { label: string; title: string; detail?: string | null };
    }
  | {
      id: string;
      role: "assistant";
      lines: string[];
      actionCard?: { title: string; actions: AssistantAction[] } | null;
      profileQuestions?: NonNullable<
        NonNullable<AssistantTurnResponse["local_reply"]>["profile_questions"]
      >;
    };

function readStoredId(projectId: number | null): number | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { id?: number; projectId?: number | null };
    if (typeof parsed.id !== "number") return null;
    if ((parsed.projectId ?? null) !== (projectId ?? null)) return null;
    return parsed.id;
  } catch {
    return null;
  }
}

function storeId(id: number, projectId: number | null) {
  try {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ id, projectId: projectId ?? null }),
    );
  } catch {
    /* ignore */
  }
}

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function ChoiceList({
  options,
  onPick,
  multi,
  selected,
}: {
  options: { id: string; label: string }[];
  onPick: (id: string) => void;
  multi?: boolean;
  selected?: string[];
}) {
  return (
    <ul className="mt-2.5 space-y-1.5">
      {options.map((o) => {
        const active = selected?.includes(o.id);
        return (
          <li key={o.id}>
            <button
              type="button"
              onClick={() => onPick(o.id)}
              className={cn(
                "flex w-full items-center gap-2 rounded-md border px-2.5 py-2 text-left text-[13px] transition-colors",
                active
                  ? "border-primary/45 bg-primary/8 font-medium text-foreground"
                  : "border-border/70 bg-background text-foreground/90 hover:bg-muted/50",
              )}
            >
              <span
                className={cn(
                  "flex size-3.5 shrink-0 items-center justify-center border",
                  multi ? "rounded-sm" : "rounded-full",
                  active
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border",
                )}
                aria-hidden
              >
                {active ? <Check className="size-2.5" /> : null}
              </span>
              {o.label}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function IntentCard({
  meta,
  text,
}: {
  meta?: { label: string; title: string; detail?: string | null };
  text: string;
}) {
  const label = meta?.label || "Research";
  const title = meta?.title || text;
  return (
    <div className="rounded-lg border border-primary/35 bg-primary/[0.09] px-2.5 py-2 text-left shadow-[inset_3px_0_0_0_var(--primary)]">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-primary">{label}</p>
      <p className="mt-0.5 text-[13px] font-medium leading-snug text-foreground">{title}</p>
      {meta?.detail ? (
        <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">
          Topic: {meta.detail}
        </p>
      ) : text !== title ? (
        <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">{text}</p>
      ) : null}
    </div>
  );
}

function ActionCard({
  card,
  onPick,
}: {
  card: { title: string; actions: AssistantAction[] };
  onPick: (a: AssistantAction) => void;
}) {
  return (
    <div className="rounded-lg border border-primary/30 bg-primary/[0.06] px-2.5 py-2.5">
      <p className="text-[12px] font-semibold text-foreground">{card.title}</p>
      <ul className="mt-2 space-y-1">
        {card.actions.map((a) => (
          <li key={a.id}>
            <button
              type="button"
              onClick={() => onPick(a)}
              className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[12.5px] text-foreground/90 transition-colors hover:bg-primary/10"
            >
              <span
                className="flex size-3 shrink-0 rounded-full border border-primary/50"
                aria-hidden
              />
              {a.label}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MentorOnboarding({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient();
  const [step, setStep] = useState(0);
  const [roleId, setRoleId] = useState("");
  const [experienceId, setExperienceId] = useState("");
  const [goalId, setGoalId] = useState("");
  const [fields, setFields] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function finish() {
    setBusy(true);
    setError(null);
    try {
      const role = MENTOR_ROLES.find((r) => r.id === roleId);
      const exp = MENTOR_EXPERIENCE.find((e) => e.id === experienceId);
      const goal = MENTOR_GOALS.find((g) => g.id === goalId);
      await api.post("/api/onboarding/complete", {
        research_role: role?.apiRole,
        experience_level: exp?.api,
        research_goal: goal?.apiGoal,
        research_fields: fields,
      });
      await qc.invalidateQueries({ queryKey: ["me"] });
      onDone();
    } catch {
      setError("Could not save your profile. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {step === 0 ? (
          <div className="space-y-3 text-[13px] leading-relaxed text-foreground/90">
            <p className="font-medium text-foreground">Welcome to Dhund.</p>
            <p className="text-muted-foreground">
              I&apos;ll help you from your first research question to a publishable paper.
            </p>
            <p className="text-muted-foreground">Let&apos;s understand where you&apos;re starting.</p>
            <button
              type="button"
              disabled={busy}
              onClick={() => setStep(1)}
              className="mt-2 inline-flex h-8 items-center rounded-md bg-primary px-3 text-[12px] font-medium text-primary-foreground"
            >
              Begin
            </button>
          </div>
        ) : null}
        {step === 1 ? (
          <div>
            <p className="text-[13px] font-medium text-foreground">What best describes you?</p>
            <ChoiceList
              options={MENTOR_ROLES.map((r) => ({ id: r.id, label: r.label }))}
              onPick={(id) => {
                setRoleId(id);
                setStep(2);
              }}
            />
          </div>
        ) : null}
        {step === 2 ? (
          <div>
            <p className="text-[13px] font-medium text-foreground">
              How experienced are you with research?
            </p>
            <ChoiceList
              options={MENTOR_EXPERIENCE.map((e) => ({ id: e.id, label: e.label }))}
              onPick={(id) => {
                setExperienceId(id);
                setStep(3);
              }}
            />
          </div>
        ) : null}
        {step === 3 ? (
          <div>
            <p className="text-[13px] font-medium text-foreground">What do you want to achieve?</p>
            <ChoiceList
              options={MENTOR_GOALS.map((g) => ({ id: g.id, label: g.label }))}
              onPick={(id) => {
                setGoalId(id);
                setStep(4);
              }}
            />
          </div>
        ) : null}
        {step === 4 ? (
          <div>
            <p className="text-[13px] font-medium text-foreground">What field are you working in?</p>
            <ChoiceList
              multi
              selected={fields}
              options={MENTOR_FIELDS}
              onPick={(id) =>
                setFields((prev) =>
                  prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id].slice(0, 6),
                )
              }
            />
            <button
              type="button"
              disabled={busy || fields.length === 0}
              onClick={() => void finish()}
              className="mt-3 inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-[12px] font-medium text-primary-foreground disabled:opacity-40"
            >
              {busy ? <Loader2 className="size-3.5 animate-spin" /> : null}
              Continue with Dhund
            </button>
          </div>
        ) : null}
        {error ? <p className="text-[12px] text-destructive">{error}</p> : null}
      </div>
      <div className="shrink-0 border-t border-border/40 px-4 py-2">
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            void (async () => {
              setBusy(true);
              try {
                await api.post("/api/onboarding/complete", {
                  skipped: true,
                  research_goal: "explore",
                });
                await qc.invalidateQueries({ queryKey: ["me"] });
                onDone();
              } finally {
                setBusy(false);
              }
            })()
          }
          className="text-[11px] text-muted-foreground hover:text-foreground"
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}

function ComposerBar({
  draft,
  setDraft,
  placeholder,
  busy,
  streaming,
  onSend,
  onStop,
  inputRef,
}: {
  draft: string;
  setDraft: (v: string) => void;
  placeholder: string;
  busy: boolean;
  streaming?: boolean;
  onSend: () => void;
  onStop?: () => void;
  inputRef?: React.RefObject<HTMLTextAreaElement | null>;
}) {
  return (
    <div className="shrink-0 border-t border-border/40 px-3 py-2.5">
      <div className="flex items-end gap-1.5 rounded-lg border border-border/70 bg-background px-2 py-1.5 focus-within:border-border">
        <textarea
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          rows={2}
          placeholder={placeholder}
          disabled={busy || streaming}
          className="max-h-28 min-h-[2.5rem] flex-1 resize-none bg-transparent py-1 text-[13px] outline-none placeholder:text-muted-foreground disabled:opacity-60"
        />
        {streaming ? (
          <button
            type="button"
            onClick={onStop}
            className="mb-0.5 flex size-7 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
            aria-label="Stop"
          >
            <Square className="size-3.5" />
          </button>
        ) : (
          <button
            type="button"
            onClick={onSend}
            disabled={!draft.trim() || busy}
            className="mb-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground disabled:opacity-40"
            aria-label="Send"
          >
            {busy ? <Loader2 className="size-3.5 animate-spin" /> : <ArrowUp className="size-3.5" />}
          </button>
        )}
      </div>
    </div>
  );
}

function Thread({
  conversationId,
  pendingText,
  pendingMode,
  onConsumedPending,
  placeholder,
  onLocalHandled,
}: {
  conversationId: number;
  pendingText: string | null;
  pendingMode?: string | null;
  onConsumedPending: () => void;
  placeholder: string;
  onLocalHandled: (text: string) => void;
}) {
  const qc = useQueryClient();
  const { defaultModel, defaultSearchMode, currentProjectId } = useUI();
  const { data: me } = useMe();
  const { data: conv } = useConversation(conversationId);
  const stream = useChatStream(conversationId);
  const [draft, setDraft] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const pendingSent = useRef(false);
  const model = defaultModel || me?.default_model || "gpt-4o-mini";
  const messages = conv?.messages ?? [];

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages.length, stream.streamingText]);

  useEffect(() => {
    if (!pendingText || pendingSent.current || stream.isStreaming) return;
    pendingSent.current = true;
    const text = pendingText;
    const mode = pendingMode || undefined;
    onConsumedPending();
    appendUserMessage(qc, conversationId, text, []);
    void stream.send({
      conversation_id: conversationId,
      message: text,
      model,
      search: defaultSearchMode || "auto",
      skill: "ask",
      assistant_mode: mode,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingText, conversationId]);

  async function send() {
    const text = draft.trim();
    if (!text || stream.isStreaming) return;
    setDraft("");
    try {
      const decision = await assistantApi.turn({
        message: text,
        project_id: currentProjectId,
        surface: "home",
        conversation_id: conversationId,
      });
      if (decision.outcome !== "start_job") {
        onLocalHandled(text);
        return;
      }
      appendUserMessage(qc, conversationId, text, []);
      await stream.send({
        conversation_id: conversationId,
        message: text,
        model,
        search: defaultSearchMode || "auto",
        skill: "ask",
        assistant_mode: decision.start_job?.mode,
      });
      return;
    } catch {
      /* fall through to stream */
    }
    appendUserMessage(qc, conversationId, text, []);
    await stream.send({
      conversation_id: conversationId,
      message: text,
      model,
      search: defaultSearchMode || "auto",
      skill: "ask",
    });
  }

  return (
    <>
      <div ref={listRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.map((m) =>
          m.role === "user" ? (
            <IntentCard key={m.id} text={m.content} />
          ) : (
            <div
              key={m.id}
              className="px-1 py-1 text-[13px] leading-relaxed text-foreground/90 whitespace-pre-wrap"
            >
              {m.content}
            </div>
          ),
        )}
        {stream.isStreaming || stream.streamingText ? (
          <div className="px-1 py-1 text-[13px] leading-relaxed whitespace-pre-wrap">
            {stream.streamingText || (
              <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin" />
                Working…
              </span>
            )}
          </div>
        ) : null}
        {stream.error ? <p className="text-[12px] text-destructive">{stream.error}</p> : null}
      </div>
      <ComposerBar
        draft={draft}
        setDraft={setDraft}
        placeholder={placeholder}
        busy={false}
        streaming={stream.isStreaming}
        onSend={() => void send()}
        onStop={() => stream.stop()}
      />
      <p className="px-3 pb-2 text-[11px] text-muted-foreground">
        <Link to={`/c/${conversationId}`} className="hover:underline">
          Open full chat
        </Link>
      </p>
    </>
  );
}

export function HomeAssistantPanel({ firstName }: { firstName: string }) {
  const navigate = useNavigate();
  const { currentProjectId, defaultModel } = useUI();
  const { data: me, refetch: refetchMe } = useMe();
  const createConversation = useCreateConversation();
  const [conversationId, setConversationId] = useState<number | null>(() =>
    readStoredId(currentProjectId),
  );
  const [pendingText, setPendingText] = useState<string | null>(null);
  const [pendingMode, setPendingMode] = useState<string | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const [localTurns, setLocalTurns] = useState<LocalTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [turnBusy, setTurnBusy] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const scopedProject = useRef(currentProjectId);
  const seeded = useRef(false);

  const needsOnboarding = me != null && !me.onboarding_completed;
  const placeholder = "What would you like to work on?";

  useEffect(() => {
    if (scopedProject.current === currentProjectId) return;
    scopedProject.current = currentProjectId;
    setConversationId(readStoredId(currentProjectId));
    setPendingText(null);
    setPendingMode(null);
    setBootError(null);
    setLocalTurns([]);
    seeded.current = false;
  }, [currentProjectId]);

  useEffect(() => {
    if (needsOnboarding || conversationId != null || seeded.current || me == null) return;
    seeded.current = true;
    void (async () => {
      try {
        const session = await assistantApi.session(currentProjectId);
        const lr = session.local_reply;
        // Home left column owns the primary CTA — mentor is companion, not a second dashboard.
        const lines = (lr?.lines ?? []).filter(
          (line) =>
            !/what are you trying to accomplish/i.test(line) &&
            !/before we continue/i.test(line),
        );
        setLocalTurns([
          {
            id: uid(),
            role: "assistant",
            lines:
              lines.length > 0
                ? lines.slice(0, 3)
                : [
                    `Good to see you${firstName ? `, ${firstName}` : ""}.`,
                    "Ask about your research anytime.",
                  ],
            // No actionCard on open — Invisible Intelligence / one recommendation on Home.
            actionCard: null,
          },
        ]);
      } catch {
        setLocalTurns([
          {
            id: uid(),
            role: "assistant",
            lines: [
              `Good to see you${firstName ? `, ${firstName}` : ""}.`,
              "Ask about your research anytime.",
            ],
          },
        ]);
      }
    })();
  }, [needsOnboarding, me, conversationId, currentProjectId, firstName]);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [localTurns]);

  function applyLocalDecision(text: string, decision: AssistantTurnResponse) {
    setLocalTurns((prev) => [
      ...prev,
      {
        id: uid(),
        role: "user",
        text,
        meta: decision.intent_meta,
      },
      {
        id: uid(),
        role: "assistant",
        lines: decision.local_reply?.lines ?? [],
        actionCard: decision.local_reply?.action_card,
        profileQuestions: decision.local_reply?.profile_questions,
      },
    ]);
  }

  async function startResearchChat(text: string, mode?: string) {
    setBootError(null);
    try {
      const model = defaultModel || me?.default_model || "gpt-4o-mini";
      const conv = await createConversation.mutateAsync({
        model,
        project_id: currentProjectId ?? null,
      });
      storeId(conv.id, currentProjectId);
      setPendingMode(mode || null);
      setPendingText(text);
      setConversationId(conv.id);
      setLocalTurns([]);
    } catch {
      setBootError("Could not start that task. Try again.");
    }
  }

  async function handleSubmit() {
    const text = draft.trim();
    if (!text || turnBusy) return;
    setDraft("");
    setTurnBusy(true);
    try {
      const decision = await assistantApi.turn({
        message: text,
        project_id: currentProjectId,
        surface: "home",
      });
      if (decision.outcome === "start_job") {
        setLocalTurns((prev) => [
          ...prev,
          {
            id: uid(),
            role: "user",
            text,
            meta: decision.intent_meta,
          },
        ]);
        await startResearchChat(
          decision.start_job?.message || text,
          decision.start_job?.mode || decision.mode,
        );
        return;
      }
      applyLocalDecision(text, decision);
    } catch {
      setBootError("Assistant unavailable. Try again.");
    } finally {
      setTurnBusy(false);
    }
  }

  function handleAction(action: AssistantAction) {
    setLocalTurns((prev) => [
      ...prev,
      {
        id: uid(),
        role: "user",
        text: action.label,
        meta: { label: "Workflow task", title: action.label },
      },
    ]);
    if (action.focus_composer) {
      setLocalTurns((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          lines: ["What research question do you want to explore?"],
        },
      ]);
      requestAnimationFrame(() => inputRef.current?.focus());
      return;
    }
    if (action.href) {
      setLocalTurns((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          lines: [`Opening ${action.label.toLowerCase()}…`],
        },
      ]);
      navigate(action.href);
    }
  }

  async function handleProfilePick(questionId: string, optionId: string, optionLabel: string) {
    // Persist experience when answered; second question continues via another turn.
    if (questionId === "experience") {
      try {
        await api.post("/api/onboarding/complete", {
          experience_level: optionId === "expert" ? "advanced" : optionId,
          research_goal: me?.onboarding?.research_goal || "explore",
        });
        await refetchMe();
      } catch {
        /* non-fatal */
      }
    }
    setLocalTurns((prev) => [
      ...prev,
      {
        id: uid(),
        role: "user",
        text: optionLabel,
        meta: { label: "Profile", title: optionLabel },
      },
    ]);
    if (questionId === "experience") {
      setLocalTurns((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          lines: ["What are you working on?"],
          profileQuestions: [
            {
              id: "focus",
              prompt: "What are you working on?",
              options: [
                { id: "assignment", label: "Assignment" },
                { id: "lit_review", label: "Literature Review" },
                { id: "thesis", label: "Thesis" },
                { id: "conference", label: "Conference Paper" },
                { id: "journal", label: "Journal Paper" },
              ],
            },
          ],
        },
      ]);
      return;
    }
    // focus answered → ask backend for workflow coach reply
    void (async () => {
      try {
        const decision = await assistantApi.turn({
          message: "What should I do next?",
          project_id: currentProjectId,
          surface: "home",
        });
        setLocalTurns((prev) => [
          ...prev,
          {
            id: uid(),
            role: "assistant",
            lines: decision.local_reply?.lines ?? [],
            actionCard: decision.local_reply?.action_card,
          },
        ]);
      } catch {
        /* ignore */
      }
    })();
  }

  return (
    <aside
      className="flex h-full min-h-0 w-full shrink-0 flex-col border-l border-border/50 bg-muted/15 lg:w-[300px]"
      aria-label="Research Mentor"
    >
      <div className="border-b border-border/40 px-4 py-3">
        <p className="text-[13px] font-semibold tracking-tight text-foreground">
          Research Mentor
        </p>
        <p className="mt-0.5 text-[11px] text-muted-foreground">
          {needsOnboarding
            ? "Getting to know you"
            : "Ask about your research"}
        </p>
      </div>

      {needsOnboarding ? (
        <MentorOnboarding onDone={() => void refetchMe()} />
      ) : conversationId != null ? (
        <Thread
          conversationId={conversationId}
          pendingText={pendingText}
          pendingMode={pendingMode}
          onConsumedPending={() => {
            setPendingText(null);
            setPendingMode(null);
          }}
          placeholder={placeholder}
          onLocalHandled={(text) => {
            setConversationId(null);
            setPendingText(null);
            setPendingMode(null);
            void (async () => {
              try {
                const decision = await assistantApi.turn({
                  message: text,
                  project_id: currentProjectId,
                  surface: "home",
                });
                applyLocalDecision(text, decision);
              } catch {
                /* ignore */
              }
            })();
          }}
        />
      ) : (
        <>
          <div ref={listRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {localTurns.map((t) =>
              t.role === "user" ? (
                <IntentCard key={t.id} meta={t.meta} text={t.text} />
              ) : (
                <div key={t.id} className="space-y-2.5">
                  <div className="space-y-1.5 text-[13px] leading-relaxed text-foreground/90">
                    {t.lines.map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>
                  {t.profileQuestions?.map((q) => (
                    <div
                      key={q.id}
                      className="rounded-lg border border-border/70 bg-background px-2.5 py-2.5"
                    >
                      <p className="text-[13px] font-medium text-foreground">{q.prompt}</p>
                      <ChoiceList
                        options={q.options}
                        onPick={(id) => {
                          const opt = q.options.find((o) => o.id === id);
                          if (opt) void handleProfilePick(q.id, id, opt.label);
                        }}
                      />
                    </div>
                  ))}
                  {t.actionCard ? (
                    <ActionCard card={t.actionCard} onPick={handleAction} />
                  ) : null}
                </div>
              ),
            )}
          </div>
          <ComposerBar
            draft={draft}
            setDraft={setDraft}
            placeholder={placeholder}
            busy={turnBusy || createConversation.isPending}
            onSend={() => void handleSubmit()}
            inputRef={inputRef}
          />
        </>
      )}

      {bootError ? (
        <p className="px-4 pb-3 text-[12px] text-destructive">{bootError}</p>
      ) : null}
    </aside>
  );
}
