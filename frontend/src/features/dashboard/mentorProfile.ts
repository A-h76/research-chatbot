/**
 * Research Mentor — grounded in the researcher's project & progress.
 * Tone: teach (beginner) → concise (intermediate) → sparse (expert).
 * Never lead with a capability dump.
 */

export type MentorExperience = "beginner" | "intermediate" | "advanced" | "expert";

export type MentorRoleOption = {
  id: string;
  label: string;
  apiRole: "student" | "researcher" | "professor" | "industry";
};

export type MentorGoalOption = {
  id: string;
  label: string;
  apiGoal: "publish" | "thesis" | "lit_review" | "discover" | "write" | "explore";
};

export const MENTOR_ROLES: MentorRoleOption[] = [
  { id: "undergrad", label: "Undergraduate student", apiRole: "student" },
  { id: "masters", label: "Master's student", apiRole: "student" },
  { id: "phd", label: "PhD researcher", apiRole: "researcher" },
  { id: "professor", label: "Professor", apiRole: "professor" },
  { id: "industry", label: "Industry researcher", apiRole: "industry" },
  { id: "independent", label: "Independent researcher", apiRole: "researcher" },
  { id: "other", label: "Other", apiRole: "researcher" },
];

export const MENTOR_EXPERIENCE: { id: MentorExperience; label: string; api: string }[] = [
  { id: "beginner", label: "Beginner", api: "beginner" },
  { id: "intermediate", label: "Intermediate", api: "intermediate" },
  { id: "advanced", label: "Advanced", api: "advanced" },
  { id: "expert", label: "Expert", api: "advanced" },
];

export const MENTOR_GOALS: MentorGoalOption[] = [
  { id: "lit_review", label: "Literature Review", apiGoal: "lit_review" },
  { id: "proposal", label: "Research Proposal", apiGoal: "write" },
  { id: "thesis", label: "Thesis", apiGoal: "thesis" },
  { id: "conference", label: "Conference Paper", apiGoal: "publish" },
  { id: "journal", label: "Journal Paper", apiGoal: "publish" },
  { id: "learn", label: "Learn Research", apiGoal: "discover" },
  { id: "explore", label: "Explore a Topic", apiGoal: "explore" },
];

export const MENTOR_FIELDS: { id: string; label: string }[] = [
  { id: "medicine", label: "Medicine" },
  { id: "cs", label: "Computer Science" },
  { id: "ai", label: "Artificial Intelligence" },
  { id: "physics", label: "Physics" },
  { id: "economics", label: "Economics" },
  { id: "biology", label: "Biology" },
  { id: "chemistry", label: "Chemistry" },
  { id: "engineering", label: "Engineering" },
  { id: "social", label: "Social Sciences" },
  { id: "other", label: "Other" },
];

/** Quick picks when someone says they don't know what to do today. */
export const QUICK_EXPERIENCE = [
  { id: "beginner" as const, label: "Beginner" },
  { id: "intermediate" as const, label: "Intermediate" },
  { id: "advanced" as const, label: "Advanced" },
];

export const QUICK_FOCUS = [
  { id: "assignment", label: "Assignment" },
  { id: "lit_review", label: "Literature Review" },
  { id: "thesis", label: "Thesis" },
  { id: "conference", label: "Conference Paper" },
  { id: "journal", label: "Journal Paper" },
];

export type MentorCorpusSnapshot = {
  projectName: string | null;
  papers: number;
  evidence: number;
  themes: number;
  gaps: number;
  coverage: number | null;
  contradictions: number;
  unread: number;
  hasWriting: boolean;
};

export type MentorRecommendation = {
  title: string;
  body: string;
  estimate?: string;
  actionLabel: string;
  href: string;
};

export type MentorActionId =
  | "continue_lit_review"
  | "find_papers"
  | "understand_paper"
  | "extract_evidence"
  | "discover_gaps"
  | "continue_writing"
  | "ask_question";

export type MentorAction = {
  id: MentorActionId;
  label: string;
  /** Navigate into the Research OS surface */
  href?: string;
  /** Keep user in mentor; focus composer */
  focusComposer?: boolean;
  /** Seed a concrete research chat turn (only when freeform AI is needed) */
  chatPrompt?: string;
};

export const TODAY_ACTIONS: MentorAction[] = [
  {
    id: "continue_lit_review",
    label: "Continue my literature review",
    href: "/research/compare",
  },
  {
    id: "find_papers",
    label: "Find more papers",
    href: "/library?upload=1#import",
  },
  {
    id: "understand_paper",
    label: "Understand a paper",
    href: "/library",
  },
  {
    id: "extract_evidence",
    label: "Extract evidence",
    href: "/research/compare?tab=extract",
  },
  {
    id: "discover_gaps",
    label: "Discover research gaps",
    href: "/research/compare?tab=gaps",
  },
  {
    id: "continue_writing",
    label: "Continue writing",
    href: "/writing",
  },
  {
    id: "ask_question",
    label: "Ask a research question",
    focusComposer: true,
  },
];

export type IntentKind =
  | "greeting"
  | "uncertain"
  | "workflow"
  | "research_task"
  | "writing_task"
  | "analysis_task"
  | "learning_task"
  | "research_question"
  | "chat";

export type ClassifiedIntent = {
  kind: IntentKind;
  /** Short label on the green card */
  label: string;
  /** Headline shown on the card */
  title: string;
  /** Optional secondary line (topic / detail) */
  detail?: string;
  /** True → never send to the LLM; mentor handles locally */
  localOnly: boolean;
};

export function normalizeExperience(raw: string | undefined | null): MentorExperience {
  const v = (raw || "").toLowerCase();
  if (v === "beginner" || v === "intermediate" || v === "advanced" || v === "expert") {
    return v;
  }
  return "intermediate";
}

export function isSparse(experience: MentorExperience): boolean {
  return experience === "advanced" || experience === "expert";
}

export function greetingHour(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export function mentorPlaceholder(opts: {
  experience: MentorExperience;
  goal?: string;
  projectName?: string | null;
  papers: number;
}): string {
  if (opts.papers === 0) return "Describe your research idea…";
  if (opts.experience === "beginner") return "What do you want to understand today?";
  if (opts.projectName) return "Ask about your project or research…";
  return "What would you like to work on?";
}

/** Classify a freeform user turn into a research-intent card. */
export function classifyIntent(raw: string): ClassifiedIntent {
  const text = raw.trim();
  const lower = text.toLowerCase();
  const compact = lower.replace(/[^\w\s]/g, "").trim();

  if (
    /^(hi|hello|hey|yo|sup|hiya|good\s*(morning|afternoon|evening)|howdy)(\s+.*)?$/i.test(
      compact,
    ) ||
    compact === "hi there" ||
    compact === "hello there"
  ) {
    return {
      kind: "greeting",
      label: "Greeting",
      title: text.length > 40 ? text.slice(0, 40) + "…" : text,
      localOnly: true,
    };
  }

  if (
    /^(i\s+don'?t\s+know|idk|not\s+sure|unsure|no\s+idea|help\s+me\s+decide|what\s+should\s+i\s+do|dunno)[\s.!?]*$/i.test(
      lower,
    ) ||
    /don'?t know what (to do|i('m| am) doing)/i.test(lower)
  ) {
    return {
      kind: "uncertain",
      label: "Need direction",
      title: text.length > 48 ? text.slice(0, 48) + "…" : text,
      localOnly: true,
    };
  }

  if (
    /what should i (do|work on)|next step|where (do|should) i start|recommend/i.test(lower)
  ) {
    return {
      kind: "workflow",
      label: "Workflow",
      title: "What should I do next?",
      localOnly: true,
    };
  }

  const findMatch = lower.match(
    /(?:find|search|look\s*up|get)\s+(?:more\s+)?papers?\s+(?:on|about|for)\s+(.+)/i,
  );
  if (findMatch || /find (papers|literature|articles)/i.test(lower)) {
    return {
      kind: "research_task",
      label: "Research task",
      title: "Find papers",
      detail: findMatch?.[1]?.trim() || text,
      localOnly: false,
    };
  }

  if (/^(draft|write|revise|rewrite|polish)\b/i.test(lower) || /\b(introduction|abstract|methods|discussion|conclusion)\b/i.test(lower) && /\b(draft|write|help)\b/i.test(lower)) {
    return {
      kind: "writing_task",
      label: "Writing task",
      title: text.length > 56 ? text.slice(0, 56) + "…" : text,
      localOnly: false,
    };
  }

  if (
    /\b(compare|contrast|contradict|side[- ]by[- ]side)\b/i.test(lower) ||
    /\b(theme|gap|evidence|matrix)\b/i.test(lower)
  ) {
    return {
      kind: "analysis_task",
      label: "Analysis task",
      title: text.length > 56 ? text.slice(0, 56) + "…" : text,
      localOnly: false,
    };
  }

  if (
    /^(what is|what's|whats|explain|define|how does|how do|tell me about)\b/i.test(lower) ||
    /\bexplain\b/i.test(lower)
  ) {
    return {
      kind: "learning_task",
      label: "Learning task",
      title: text.length > 56 ? text.slice(0, 56) + "…" : text,
      localOnly: false,
    };
  }

  if (/\?$/.test(text) || /^(can|could|should|is|are|does|do|will)\b/i.test(lower)) {
    return {
      kind: "research_question",
      label: "Research question",
      title: text.length > 56 ? text.slice(0, 56) + "…" : text,
      localOnly: false,
    };
  }

  if (/joke|how are you|thanks|thank you|lol|haha/i.test(lower)) {
    return {
      kind: "chat",
      label: "Chat",
      title: text.length > 48 ? text.slice(0, 48) + "…" : text,
      localOnly: false,
    };
  }

  return {
    kind: "research_question",
    label: "Research",
    title: text.length > 56 ? text.slice(0, 56) + "…" : text,
    localOnly: false,
  };
}

export function buildMentorRecommendation(
  snap: MentorCorpusSnapshot,
  experience: MentorExperience,
): MentorRecommendation {
  if (!snap.projectName || snap.papers === 0) {
    return {
      title: "Import papers",
      body:
        experience === "beginner"
          ? "Today's goal is simple: get a few papers into your library. Tomorrow we extract evidence."
          : "Import papers so Dhund can ground the next steps in your corpus.",
      estimate: "A few minutes",
      actionLabel: "Open Library",
      href: "/library?upload=1#import",
    };
  }
  if (snap.evidence === 0) {
    return {
      title: "Extract evidence",
      body:
        experience === "beginner"
          ? "You have papers. Next we pull out evidence — that's how themes and gaps appear."
          : "Highest-impact next step for this corpus.",
      estimate: "About 3 minutes",
      actionLabel: "Extract evidence",
      href: "/research/compare?tab=extract",
    };
  }
  if (snap.gaps > 0) {
    return {
      title: "Review research gaps",
      body: `${snap.gaps} gap${snap.gaps === 1 ? "" : "s"} visible from your evidence coverage.`,
      estimate: "5–10 minutes",
      actionLabel: "Review gaps",
      href: "/research/compare?tab=gaps",
    };
  }
  if (snap.contradictions > 0) {
    return {
      title: "Inspect contradictions",
      body: `${snap.contradictions} contradiction${snap.contradictions === 1 ? "" : "s"} in this corpus.`,
      actionLabel: "Open Graph",
      href: "/research/compare?tab=graph",
    };
  }
  if (!snap.hasWriting) {
    return {
      title: "Start writing",
      body:
        experience === "beginner"
          ? "Your corpus is ready enough to draft from evidence."
          : "Draft from accepted evidence.",
      actionLabel: "Open Writing",
      href: "/writing",
    };
  }
  if (snap.unread > 0) {
    return {
      title: "Unread papers",
      body: `${snap.unread} unread in your library.`,
      actionLabel: "Open unread",
      href: "/library?reading_status=unread",
    };
  }
  return {
    title: "Compare papers",
    body: "Side-by-side synthesis is the highest-leverage next move.",
    actionLabel: "Compare Papers",
    href: "/research/compare?tab=compare",
  };
}

export function buildOpeningLines(opts: {
  firstName: string;
  experience: MentorExperience;
  snap: MentorCorpusSnapshot;
  returning?: boolean;
}): string[] {
  const { firstName, experience, snap } = opts;
  const name = firstName || "there";
  const sparse = isSparse(experience);

  if (sparse) {
    const lines = [`Welcome back${firstName ? `, ${firstName}` : ""}.`];
    if (snap.projectName) {
      const bits = [`${snap.papers} papers`, `${snap.evidence} evidence`];
      if (snap.contradictions > 0) bits.push(`${snap.contradictions} contradictions`);
      lines.push(`Your corpus: ${bits.join(" · ")}`);
    }
    return lines;
  }

  const lines = [
    `${greetingHour()}, ${name}.`,
    opts.returning ? "Good to see you again." : "Let's pick up your research.",
  ];

  if (snap.projectName) {
    lines.push(`You're currently working on ${snap.projectName}.`);
  } else if (experience === "beginner") {
    lines.push("You're just getting started — I'll guide each step.");
  }

  if (experience === "beginner" && snap.papers === 0) {
    lines.push("Today's goal: import papers. I'll explain everything along the way.");
  } else if (!sparse) {
    lines.push("Before we continue — what are you trying to accomplish today?");
  }

  return lines;
}

export function buildUncertainPlan(opts: {
  experience: MentorExperience;
  focusId: string;
  snap: MentorCorpusSnapshot;
}): string[] {
  const { experience, focusId, snap } = opts;
  if (experience === "beginner") {
    return [
      "You're just starting. I'll guide you through every step.",
      "Today's goal: import papers.",
      "Next we'll extract evidence, then identify themes.",
      "Don't worry — I'll explain everything along the way.",
    ];
  }
  if (isSparse(experience)) {
    const rec = buildMentorRecommendation(snap, experience);
    return [`Focus: ${focusId.replace(/_/g, " ")}.`, `Next: ${rec.title}.`];
  }
  const rec = buildMentorRecommendation(snap, experience);
  return [
    `Working on a ${focusId.replace(/_/g, " ")}.`,
    `Recommended next: ${rec.title}.`,
    rec.body,
  ];
}

export function buildLocalMentorReply(
  intent: ClassifiedIntent,
  opts: {
    firstName: string;
    experience: MentorExperience;
    snap: MentorCorpusSnapshot;
  },
): string[] {
  if (intent.kind === "greeting") {
    return buildOpeningLines({
      firstName: opts.firstName,
      experience: opts.experience,
      snap: opts.snap,
      returning: true,
    });
  }
  if (intent.kind === "uncertain") {
    return ["No problem.", "Let's figure it out together.", "Can I ask two quick questions?"];
  }
  if (intent.kind === "workflow") {
    const rec = buildMentorRecommendation(opts.snap, opts.experience);
    if (isSparse(opts.experience)) {
      return [
        opts.snap.projectName
          ? `${opts.snap.papers} papers · ${opts.snap.evidence} evidence`
          : "No active project yet.",
        `Next: ${rec.title}.`,
      ];
    }
    return [
      opts.snap.projectName
        ? `Looking at ${opts.snap.projectName}: ${opts.snap.papers} papers, ${opts.snap.evidence} evidence, ${opts.snap.themes} themes, ${opts.snap.gaps} gaps.`
        : "You don't have an active project yet — start by importing papers.",
      `Highest-impact next step: ${rec.title}.`,
      rec.body,
      rec.estimate ? `Estimated time: ${rec.estimate}.` : "",
      "Would you like to start?",
    ].filter(Boolean);
  }
  return buildOpeningLines({
    firstName: opts.firstName,
    experience: opts.experience,
    snap: opts.snap,
    returning: true,
  });
}
