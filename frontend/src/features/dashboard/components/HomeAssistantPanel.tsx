/**
 * Home Research Mentor — supervisor-style guide + normal conversational AI.
 * First visit: one-question profile intake. After: contextual briefing + chat.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUp, Check, Loader2, Square } from "lucide-react";
import { useUI } from "@/context/UIContext";
import { useMe } from "@/features/profile/useMe";
import { useProjects } from "@/features/projects/useProjects";
import {
  useConversation,
  useCreateConversation,
} from "@/features/chat/hooks/useConversation";
import { useChatStream } from "@/features/chat/hooks/useChatStream";
import { appendUserMessage } from "@/features/chat/lib/optimistic";
import { useRiCorpusMetrics } from "@/features/analysis/hooks/useRiCorpusMetrics";
import { writingApi } from "@/features/writing/api";
import { useDashboard } from "../useDashboard";
import { api } from "@/lib/apiClient";
import { cn } from "@/lib/utils";
import {
  MENTOR_EXPERIENCE,
  MENTOR_FIELDS,
  MENTOR_GOALS,
  MENTOR_ROLES,
  buildMentorRecommendation,
  buildProgressChecks,
  greetingHour,
  mentorPlaceholder,
  normalizeExperience,
  stagesCompleted,
  type MentorCorpusSnapshot,
  type MentorExperience,
} from "../mentorProfile";

const STORAGE_KEY = "dhund:home-assistant-conversation";
const COACH_TIP_KEY = "dhund:mentor-coach-tip-dismissed";

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
    <ul className="mt-3 space-y-1.5">
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
                  ? "border-primary/40 bg-primary/5 font-medium text-foreground"
                  : "border-border/70 bg-background text-foreground/90 hover:bg-muted/50",
              )}
            >
              <span
                className={cn(
                  "flex size-3.5 shrink-0 items-center justify-center rounded-full border",
                  multi ? "rounded-sm" : "rounded-full",
                  active ? "border-primary bg-primary text-primary-foreground" : "border-border",
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
            <p className="mt-1 text-[12px] text-muted-foreground">Pick one or more.</p>
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

function MentorBriefing({
  firstName,
  experience,
  goal,
  projectName,
  snap,
  showCoachTip,
  onDismissCoach,
}: {
  firstName: string;
  experience: MentorExperience;
  goal?: string;
  projectName: string | null;
  snap: MentorCorpusSnapshot;
  showCoachTip: boolean;
  onDismissCoach: () => void;
}) {
  const rec = buildMentorRecommendation(snap, experience);
  const checks = buildProgressChecks(snap);
  const stages = stagesCompleted(snap);
  const sparse = experience === "advanced" || experience === "expert";

  return (
    <div className="space-y-3 border-b border-border/40 px-4 py-3">
      <div className="space-y-1.5 text-[13px] leading-relaxed">
        <p className="text-foreground">
          {greetingHour()}
          {firstName ? `, ${firstName}` : ""}.
        </p>
        {projectName ? (
          sparse ? (
            <p className="text-muted-foreground">
              {snap.papers} papers
              {snap.coverage != null ? ` · ${Math.round(snap.coverage * 100)}% coverage` : ""}
              {snap.contradictions > 0 ? ` · ${snap.contradictions} contradictions` : ""}
            </p>
          ) : (
            <>
              <p className="text-muted-foreground">
                You&apos;re working on <span className="text-foreground">{projectName}</span>.
              </p>
              <p className="text-[12px] text-muted-foreground">
                {stages.done} of {stages.total} research stages underway.
              </p>
            </>
          )
        ) : (
          <p className="text-muted-foreground">
            {experience === "beginner"
              ? "Today we can import papers, extract evidence, and review themes — I'll explain each step."
              : "Open or create a project to get tailored recommendations."}
          </p>
        )}
      </div>

      {!sparse && projectName ? (
        <ul className="space-y-1">
          {checks.map((c) => (
            <li
              key={c.label}
              className={cn(
                "flex items-center gap-1.5 text-[12px]",
                c.done ? "text-foreground/85" : "text-muted-foreground",
              )}
            >
              <span aria-hidden>{c.done ? "✓" : "○"}</span>
              {c.label}
            </li>
          ))}
        </ul>
      ) : null}

      {showCoachTip && experience === "beginner" && (goal === "lit_review" || goal === "thesis") ? (
        <div className="rounded-md border border-border/70 bg-background px-2.5 py-2 text-[12px] leading-relaxed text-muted-foreground">
          <p>
            I noticed this may be your first{" "}
            {goal === "lit_review" ? "literature review" : "thesis"}. Want a short explainer before
            we begin?
          </p>
          <div className="mt-2 flex gap-2">
            <Link
              to="/research/compare"
              className="font-medium text-primary hover:underline"
              onClick={onDismissCoach}
            >
              Yes
            </Link>
            <button
              type="button"
              onClick={onDismissCoach}
              className="text-muted-foreground hover:text-foreground"
            >
              Skip
            </button>
          </div>
        </div>
      ) : null}

      <div className="rounded-md border border-primary/20 bg-primary/[0.04] px-2.5 py-2">
        <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
          {sparse ? "Next" : "Recommendation"}
        </p>
        <p className="mt-0.5 text-[13px] font-medium text-foreground">{rec.title}</p>
        {!sparse ? (
          <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">{rec.body}</p>
        ) : null}
        {rec.estimate && !sparse ? (
          <p className="mt-1 text-[11px] text-muted-foreground">Estimated · {rec.estimate}</p>
        ) : null}
        <Link
          to={rec.href}
          className="mt-2 inline-flex text-[12px] font-medium text-primary hover:underline"
        >
          {rec.actionLabel} →
        </Link>
      </div>
    </div>
  );
}

function Thread({
  conversationId,
  firstName,
  pendingText,
  onConsumedPending,
  placeholder,
  briefing,
}: {
  conversationId: number;
  firstName: string;
  pendingText: string | null;
  onConsumedPending: () => void;
  placeholder: string;
  briefing: React.ReactNode;
}) {
  const qc = useQueryClient();
  const { defaultModel, defaultSearchMode } = useUI();
  const { data: me } = useMe();
  const { data: conv } = useConversation(conversationId);
  const stream = useChatStream(conversationId);
  const [draft, setDraft] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const pendingSent = useRef(false);
  const model = defaultModel || me?.default_model || "gpt-4o-mini";
  const messages = conv?.messages ?? [];
  const chatting = messages.length > 0 || stream.isStreaming || Boolean(stream.streamingText);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages.length, stream.streamingText, stream.status]);

  useEffect(() => {
    if (!pendingText || pendingSent.current || stream.isStreaming) return;
    pendingSent.current = true;
    const text = pendingText;
    onConsumedPending();
    appendUserMessage(qc, conversationId, text, []);
    void stream.send({
      conversation_id: conversationId,
      message: text,
      model,
      search: defaultSearchMode || "auto",
      skill: "ask",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingText, conversationId]);

  async function send() {
    const text = draft.trim();
    if (!text || stream.isStreaming) return;
    setDraft("");
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
      {!chatting ? briefing : null}
      <div ref={listRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {chatting
          ? messages.map((m) => (
              <div
                key={m.id}
                className={cn(
                  "rounded-lg px-2.5 py-2 text-[13px] leading-relaxed",
                  m.role === "user"
                    ? "bg-muted/60 text-foreground"
                    : "text-foreground/90",
                )}
              >
                {m.content}
              </div>
            ))
          : null}
        {stream.isStreaming || stream.streamingText ? (
          <div className="rounded-lg px-2.5 py-2 text-[13px] leading-relaxed text-foreground/90">
            {stream.streamingText || (
              <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                <Loader2 className="size-3.5 animate-spin" />
                {stream.status || "Thinking…"}
              </span>
            )}
          </div>
        ) : null}
        {stream.error ? (
          <p className="px-1 text-[12px] text-destructive">{stream.error}</p>
        ) : null}
        {!chatting ? (
          <p className="text-[12px] text-muted-foreground">
            Ask anything — research questions, explanations, or just chat.
          </p>
        ) : null}
      </div>

      <div className="shrink-0 border-t border-border/40 px-3 py-2.5">
        <div className="flex items-end gap-1.5 rounded-lg border border-border/70 bg-background px-2 py-1.5 focus-within:border-border">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            rows={2}
            placeholder={placeholder}
            disabled={stream.isStreaming}
            className="max-h-28 min-h-[2.5rem] flex-1 resize-none bg-transparent py-1 text-[13px] outline-none placeholder:text-muted-foreground disabled:opacity-60"
          />
          {stream.isStreaming ? (
            <button
              type="button"
              onClick={() => stream.stop()}
              className="mb-0.5 flex size-7 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label="Stop"
            >
              <Square className="size-3.5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void send()}
              disabled={!draft.trim()}
              className="mb-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground disabled:opacity-40"
              aria-label="Send"
            >
              <ArrowUp className="size-3.5" />
            </button>
          )}
        </div>
        <p className="mt-1.5 px-0.5 text-[11px] text-muted-foreground">
          <Link to={`/c/${conversationId}`} className="hover:text-foreground hover:underline">
            Open full chat
          </Link>
          {firstName ? null : null}
        </p>
      </div>
    </>
  );
}

function BootstrapComposer({
  briefing,
  placeholder,
  busy,
  onSubmit,
}: {
  briefing: React.ReactNode;
  placeholder: string;
  busy: boolean;
  onSubmit: (text: string) => void;
}) {
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function submit() {
    const text = draft.trim();
    if (!text || busy) return;
    setDraft("");
    onSubmit(text);
  }

  return (
    <>
      {briefing}
      <div className="min-h-0 flex-1 px-4 py-3">
        <p className="text-[12px] text-muted-foreground">
          Ask anything — research questions, explanations, or just chat.
        </p>
      </div>
      <div className="shrink-0 border-t border-border/40 px-3 py-2.5">
        <div className="flex items-end gap-1.5 rounded-lg border border-border/70 bg-background px-2 py-1.5 focus-within:border-border">
          <textarea
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={2}
            placeholder={placeholder}
            disabled={busy}
            className="max-h-28 min-h-[2.5rem] flex-1 resize-none bg-transparent py-1 text-[13px] outline-none placeholder:text-muted-foreground disabled:opacity-60"
          />
          <button
            type="button"
            onClick={submit}
            disabled={!draft.trim() || busy}
            className="mb-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground disabled:opacity-40"
            aria-label="Send"
          >
            {busy ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <ArrowUp className="size-3.5" />
            )}
          </button>
        </div>
      </div>
    </>
  );
}

export function HomeAssistantPanel({ firstName }: { firstName: string }) {
  const { currentProjectId, defaultModel } = useUI();
  const { data: me, refetch: refetchMe } = useMe();
  const { data: projects = [] } = useProjects();
  const { data: dash } = useDashboard();
  const metrics = useRiCorpusMetrics(currentProjectId);
  const createConversation = useCreateConversation();
  const [conversationId, setConversationId] = useState<number | null>(() =>
    readStoredId(currentProjectId),
  );
  const [pendingText, setPendingText] = useState<string | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const [coachDismissed, setCoachDismissed] = useState(() => {
    try {
      return localStorage.getItem(COACH_TIP_KEY) === "1";
    } catch {
      return false;
    }
  });
  const scopedProject = useRef(currentProjectId);

  const writingProjectId = currentProjectId ?? dash?.projects[0]?.id ?? null;
  const { data: writingList } = useQuery({
    queryKey: ["launchpad", "writing", writingProjectId],
    queryFn: () => writingApi.listDocuments(writingProjectId as number),
    enabled: writingProjectId != null,
    staleTime: 60_000,
  });

  const project = useMemo(
    () => (currentProjectId != null ? projects.find((p) => p.id === currentProjectId) : null),
    [projects, currentProjectId],
  );

  const experience = normalizeExperience(me?.onboarding?.experience_level);
  const goal = me?.onboarding?.research_goal || me?.onboarding?.goal || "";

  const snap = useMemo(
    () => ({
      projectName: project?.name ?? null,
      papers: metrics.papers || 0,
      evidence: metrics.evidence,
      themes: metrics.themes,
      gaps: metrics.gaps,
      coverage: metrics.coverage,
      contradictions: metrics.contradictions,
      unread: dash?.library.unread ?? 0,
      hasWriting: (writingList?.items?.length ?? 0) > 0,
    }),
    [project, metrics, dash, writingList],
  );

  const placeholder = mentorPlaceholder({
    experience,
    goal,
    projectName: snap.projectName,
    papers: snap.papers,
  });

  useEffect(() => {
    if (scopedProject.current === currentProjectId) return;
    scopedProject.current = currentProjectId;
    setConversationId(readStoredId(currentProjectId));
    setPendingText(null);
    setBootError(null);
  }, [currentProjectId]);

  const needsOnboarding = me != null && !me.onboarding_completed;

  async function startWithMessage(text: string) {
    setBootError(null);
    try {
      const model = defaultModel || me?.default_model || "gpt-4o-mini";
      const conv = await createConversation.mutateAsync({
        model,
        project_id: currentProjectId ?? null,
      });
      storeId(conv.id, currentProjectId);
      setPendingText(text);
      setConversationId(conv.id);
    } catch {
      setBootError("Could not start chat. Try again.");
    }
  }

  function dismissCoach() {
    setCoachDismissed(true);
    try {
      localStorage.setItem(COACH_TIP_KEY, "1");
    } catch {
      /* ignore */
    }
  }

  const briefing = (
    <MentorBriefing
      firstName={firstName}
      experience={experience}
      goal={goal}
      projectName={snap.projectName}
      snap={snap}
      showCoachTip={!coachDismissed}
      onDismissCoach={dismissCoach}
    />
  );

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
            : currentProjectId != null
              ? "Guiding your current project"
              : "Your research companion"}
        </p>
      </div>

      {needsOnboarding ? (
        <MentorOnboarding
          onDone={() => {
            void refetchMe();
          }}
        />
      ) : conversationId != null ? (
        <Thread
          conversationId={conversationId}
          firstName={firstName}
          pendingText={pendingText}
          onConsumedPending={() => setPendingText(null)}
          placeholder={placeholder}
          briefing={briefing}
        />
      ) : (
        <BootstrapComposer
          briefing={briefing}
          placeholder={placeholder}
          busy={createConversation.isPending}
          onSubmit={(text) => void startWithMessage(text)}
        />
      )}

      {bootError ? (
        <p className="px-4 pb-3 text-[12px] text-destructive">{bootError}</p>
      ) : null}
    </aside>
  );
}
