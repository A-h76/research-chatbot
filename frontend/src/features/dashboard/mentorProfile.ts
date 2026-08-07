/**
 * Research Mentor — profile-aware briefing + copy for the Home assistant.
 * Tone scales by experience: teach (beginner) → concise (intermediate) → sparse (expert/advanced).
 */

export type MentorExperience = "beginner" | "intermediate" | "advanced" | "expert";

export type MentorRoleOption = {
  id: string;
  label: string;
  /** Value sent to /api/onboarding/complete */
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

export function normalizeExperience(raw: string | undefined | null): MentorExperience {
  const v = (raw || "").toLowerCase();
  if (v === "beginner" || v === "intermediate" || v === "advanced" || v === "expert") {
    return v;
  }
  return "intermediate";
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
  const goal = (opts.goal || "").toLowerCase();
  if (opts.papers === 0) {
    if (goal.includes("lit") || goal === "lit_review") {
      return "What research question are you exploring?";
    }
    return "Describe your research idea…";
  }
  if (opts.experience === "beginner") {
    return "Need help with your literature review?";
  }
  if (opts.projectName) {
    return "Ask about your project or research…";
  }
  return "What would you like to understand today?";
}

export function buildMentorRecommendation(
  snap: MentorCorpusSnapshot,
  experience: MentorExperience,
): MentorRecommendation {
  if (!snap.projectName || snap.papers === 0) {
    return {
      title: "Start your corpus",
      body:
        experience === "beginner"
          ? "Upload a few papers related to your topic. I'll help you turn them into evidence, themes, and a draft."
          : "Import papers into a project so Dhund can extract evidence and guide synthesis.",
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
          ? "You have papers. Next we extract evidence — claims Dhund can cite, theme, and compare. Without this step, themes and gaps stay empty."
          : "Highest-impact next step: extract evidence so themes, gaps, and synthesis unlock.",
      estimate: "About 3 minutes",
      actionLabel: "Open Research Intelligence",
      href: "/research/compare?tab=extract",
    };
  }
  if (snap.gaps > 0) {
    return {
      title: "Review research gaps",
      body: `${snap.gaps} gap${snap.gaps === 1 ? "" : "s"} detected from your evidence coverage.`,
      estimate: "5–10 minutes",
      actionLabel: "Review gaps",
      href: "/research/compare?tab=gaps",
    };
  }
  if (snap.contradictions > 0) {
    return {
      title: "Inspect contradictions",
      body: "Conflicting evidence appears in this corpus — worth resolving before you write.",
      actionLabel: "Open Graph",
      href: "/research/compare?tab=graph",
    };
  }
  if (!snap.hasWriting) {
    return {
      title: "Start writing from evidence",
      body:
        experience === "beginner"
          ? "Your corpus is ready enough to draft a grounded literature review."
          : "Corpus is ready — draft from accepted evidence.",
      actionLabel: "Open Writing",
      href: "/writing",
    };
  }
  if (snap.unread > 0) {
    return {
      title: "Catch up on unread papers",
      body: `${snap.unread} unread paper${snap.unread === 1 ? "" : "s"} in your library.`,
      actionLabel: "Open unread",
      href: "/library?reading_status=unread",
    };
  }
  return {
    title: "Compare key papers",
    body: "Your project has evidence — side-by-side comparison is the next synthesis step.",
    actionLabel: "Compare Papers",
    href: "/research/compare?tab=compare",
  };
}

export function buildProgressChecks(snap: MentorCorpusSnapshot): { label: string; done: boolean }[] {
  return [
    { label: "Papers imported", done: snap.papers > 0 },
    { label: "Evidence extracted", done: snap.evidence > 0 },
    { label: "Themes available", done: snap.themes > 0 },
    { label: "Writing started", done: snap.hasWriting },
  ];
}

export function stagesCompleted(snap: MentorCorpusSnapshot): { done: number; total: number } {
  const checks = buildProgressChecks(snap);
  const extra = [
    snap.gaps > 0 || snap.evidence > 0,
    snap.hasWriting,
  ];
  const done = checks.filter((c) => c.done).length + extra.filter(Boolean).length;
  return { done: Math.min(6, done), total: 6 };
}
