import type { LucideIcon } from "lucide-react";
import {
  ClipboardList,
  FlaskConical,
  GitCompare,
  History,
  LayoutDashboard,
  Network,
  SearchX,
  Table2,
  Tags,
} from "lucide-react";

/** Leaf lenses + Mission Control + workflow category landings. */
export type RiTab =
  | "overview"
  | "understand"
  | "relationships"
  | "insights"
  | "synthesis"
  | "matrix"
  | "extract"
  | "themes"
  | "gaps"
  | "graph"
  | "timeline"
  | "methodology"
  | "compare";

export type RiCategoryId = "understand" | "relationships" | "insights" | "synthesis";

export type RiLeafTab = Exclude<RiTab, "overview" | RiCategoryId>;

export type RiNavItem = {
  key: RiTab;
  label: string;
  icon: LucideIcon;
  question: string;
};

export type RiCategoryDef = {
  id: RiCategoryId;
  label: string;
  /** One-line researcher job for the category landing. */
  job: string;
  question: string;
  children: RiNavItem[];
};

export const RI_OVERVIEW: RiNavItem = {
  key: "overview",
  label: "Overview",
  icon: LayoutDashboard,
  question: "What should I do next with this corpus?",
};

export const RI_CATEGORIES: RiCategoryDef[] = [
  {
    id: "understand",
    label: "Understand",
    job: "See what the literature says — coverage, themes, and structured evidence.",
    question: "What does this corpus contain?",
    children: [
      {
        key: "matrix",
        label: "Evidence Matrix",
        icon: Table2,
        question: "What does every paper say?",
      },
      {
        key: "extract",
        label: "Structured Evidence",
        icon: ClipboardList,
        question: "What has been extracted?",
      },
      {
        key: "themes",
        label: "Themes",
        icon: Tags,
        question: "What topics emerge?",
      },
    ],
  },
  {
    id: "relationships",
    label: "Relationships",
    job: "Trace how papers, evidence, and themes connect over time.",
    question: "How are ideas connected?",
    children: [
      {
        key: "graph",
        label: "Graph",
        icon: Network,
        question: "How are ideas connected?",
      },
      {
        key: "timeline",
        label: "Timeline",
        icon: History,
        question: "How has the field evolved?",
      },
    ],
  },
  {
    id: "insights",
    label: "Insights",
    job: "Find what's missing, weak, or methodologically uneven.",
    question: "What's missing or weak?",
    children: [
      {
        key: "gaps",
        label: "Research Gaps",
        icon: SearchX,
        question: "What's missing?",
      },
      {
        key: "methodology",
        label: "Method Review",
        icon: FlaskConical,
        question: "Are methodologies strong?",
      },
    ],
  },
  {
    id: "synthesis",
    label: "Synthesis",
    job: "Compare studies and prepare evidence-grounded writing.",
    question: "How do studies differ — and what can I write?",
    children: [
      {
        key: "compare",
        label: "Compare Papers",
        icon: GitCompare,
        question: "How do studies differ?",
      },
    ],
  },
];

const ALL_TABS = new Set<string>([
  "overview",
  ...RI_CATEGORIES.map((c) => c.id),
  ...RI_CATEGORIES.flatMap((c) => c.children.map((ch) => ch.key)),
]);

export function parseRiTab(raw: string | null): RiTab {
  if (raw && ALL_TABS.has(raw)) return raw as RiTab;
  return "overview";
}

export function categoryForTab(tab: RiTab): RiCategoryId | null {
  if (tab === "overview") return null;
  if (RI_CATEGORIES.some((c) => c.id === tab)) return tab as RiCategoryId;
  for (const c of RI_CATEGORIES) {
    if (c.children.some((ch) => ch.key === tab)) return c.id;
  }
  return null;
}

export function questionForTab(tab: RiTab): string {
  if (tab === RI_OVERVIEW.key) return RI_OVERVIEW.question;
  const cat = RI_CATEGORIES.find((c) => c.id === tab);
  if (cat) return cat.question;
  for (const c of RI_CATEGORIES) {
    const child = c.children.find((ch) => ch.key === tab);
    if (child) return child.question;
  }
  return RI_OVERVIEW.question;
}

export function navCategories(showCompare: boolean): RiCategoryDef[] {
  return RI_CATEGORIES.map((c) => {
    if (c.id !== "synthesis") return c;
    return {
      ...c,
      children: showCompare ? c.children : [],
    };
  });
}
