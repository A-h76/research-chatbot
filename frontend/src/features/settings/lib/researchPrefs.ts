/** Client-side research workflow preferences (Phase A Settings). */

export type ExportBundlePref = "md_bib" | "md";

export type ResearchPrefs = {
  /** Show demoted AI Compare tab on Research. Default false (evidence-first). */
  showAiCompare: boolean;
  /** Literature-review export: Markdown only, or Markdown + BibTeX when available. */
  exportBundle: ExportBundlePref;
  /** Soft preference until CSL pipeline exists. */
  citationStyle: "apa" | "ieee" | "chicago" | "harvard" | "other";
  /** After accepting evidence, jump to Writing desk. */
  openWritingAfterAccept: boolean;
};

const KEY = "dhund.researchPrefs";

const DEFAULTS: ResearchPrefs = {
  showAiCompare: false,
  exportBundle: "md_bib",
  citationStyle: "apa",
  openWritingAfterAccept: false,
};

export function loadResearchPrefs(): ResearchPrefs {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULTS };
    const parsed = JSON.parse(raw) as Partial<ResearchPrefs>;
    return { ...DEFAULTS, ...parsed };
  } catch {
    return { ...DEFAULTS };
  }
}

export function saveResearchPrefs(patch: Partial<ResearchPrefs>): ResearchPrefs {
  const next = { ...loadResearchPrefs(), ...patch };
  localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}
