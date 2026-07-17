import type { SearchMode } from "@/types/api";

export const SEARCH_MODES: { value: SearchMode; label: string }[] = [
  { value: "off", label: "Search off" },
  { value: "auto", label: "Auto (model decides)" },
  { value: "on", label: "Always search" },
];

export const REASONING_EFFORTS = ["low", "medium", "high"] as const;

export const IMPORTANCE_RANGE = [1, 2, 3, 4, 5] as const;

export const SUGGESTIONS = [
  { title: "Summarize a research paper", prompt: "Summarize the attached research paper, highlighting its methodology, key findings, and limitations." },
  { title: "Generate literature review", prompt: "Help me write a literature review on my research topic, organized by theme." },
  { title: "Explain this dataset", prompt: "Explain the structure and key patterns in this dataset." },
  { title: "Create Python analysis", prompt: "Write Python code to analyze and visualize this data." },
  { title: "Help me write a thesis chapter", prompt: "Help me outline and draft a chapter of my thesis." },
  { title: "Find related papers", prompt: "Search the web for recent papers related to my research area." },
];
