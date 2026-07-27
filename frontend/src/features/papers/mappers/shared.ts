/**
 * Shared helpers for Paper Workspace phase mappers.
 * Components must not use these against raw phase JSON — mappers only.
 */

export function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export function asString(v: unknown): string | undefined {
  return typeof v === "string" && v.trim() ? v : undefined;
}

export function asNumber(v: unknown): number | undefined {
  return typeof v === "number" && Number.isFinite(v) ? v : undefined;
}

export function asBoolean(v: unknown): boolean | undefined {
  return typeof v === "boolean" ? v : undefined;
}

export function asStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string" && x.trim().length > 0);
}

/** Strip escaped markdown artifacts from backend prose (`\_`, `\(`, `\)`). */
export function cleanMarkdownArtifacts(raw: string): string {
  return raw.replace(/\\([_()[\]])/g, "$1");
}

export function formatLabel(raw: string): string {
  return raw
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function formatConfidence(n: number | undefined): string | undefined {
  if (n == null) return undefined;
  if (n >= 0 && n <= 1) return `${Math.round(n * 100)}%`;
  return String(n);
}

export type EvidenceRefView = {
  page?: number;
  section?: string;
  paragraph?: number;
  characterRange?: [number, number];
  textSnippet?: string;
  confidence?: number;
};

function asCharacterRange(v: unknown): [number, number] | undefined {
  if (!Array.isArray(v) || v.length < 2) return undefined;
  const a = asNumber(v[0]);
  const b = asNumber(v[1]);
  if (a == null || b == null) return undefined;
  return [a, b];
}

/** Normalize object | null | array → consistent evidence list. */
export function normalizeEvidence(raw: unknown): EvidenceRefView[] {
  if (raw == null) return [];
  const items = Array.isArray(raw) ? raw : [raw];
  const out: EvidenceRefView[] = [];
  for (const item of items) {
    if (!isRecord(item)) continue;
    const snippet = asString(item.text_snippet);
    const page = asNumber(item.page);
    const section = asString(item.section);
    const paragraph = asNumber(item.paragraph);
    const characterRange = asCharacterRange(item.character_range);
    const confidence = asNumber(item.confidence);
    if (
      snippet == null &&
      page == null &&
      section == null &&
      paragraph == null &&
      characterRange == null &&
      confidence == null
    ) {
      continue;
    }
    out.push({
      page,
      section,
      paragraph,
      characterRange,
      textSnippet: snippet,
      confidence,
    });
  }
  return out;
}

/** Normalize `GradingFramework.GRADE` / `GRADE` / `grade` → `grade`. */
export function normalizeFrameworkId(raw: string): string {
  let s = raw.trim();
  const dot = s.lastIndexOf(".");
  if (dot >= 0) s = s.slice(dot + 1);
  return s.toLowerCase();
}

/** Normalize `BiasType.RANDOMIZATION` → display "Randomization". */
export function humanizeEnumKey(raw: string): string {
  let s = raw.trim();
  const dot = s.lastIndexOf(".");
  if (dot >= 0) s = s.slice(dot + 1);
  return formatLabel(s.toLowerCase());
}
