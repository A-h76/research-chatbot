/**
 * Best-effort citation preview from a raw bibliography line.
 * Graceful: never invent DOI/year/journal when uncertain.
 */

export type CitationPreview = {
  id: string;
  raw: string;
  /** Short author line for the row, e.g. "Guilliams M." */
  authorsLine?: string;
  /** Short title / remainder preview */
  titleLine?: string;
  journal?: string;
  year?: number;
  doi?: string;
  /** True when we extracted at least authors or year/journal/doi beyond raw. */
  parsed: boolean;
};

const DOI_RE = /\b(?:doi:\s*|https?:\/\/(?:dx\.)?doi\.org\/)(10\.\S+)/i;
const YEAR_RE = /\b(19|20)\d{2}\b/;
/** "Journal Name. 2016" or "Immunity. 2016;" near the end */
const JOURNAL_YEAR_RE =
  /([A-Z][A-Za-z0-9 &'\-.]{2,80}?)\.?\s*[,(]?\s*((?:19|20)\d{2})\b/;

function stripLeadingNumber(raw: string): string {
  return raw.replace(/^\s*\[\d+\]\s*/, "").replace(/^\s*\d+\.\s+/, "").trim();
}

/**
 * Heuristic split: "Authors. Title. Journal. Year." (Vancouver-ish).
 * Falls back to a truncated raw preview when structure is unclear.
 */
export function parseCitationPreview(raw: string, index: number): CitationPreview {
  const cleaned = stripLeadingNumber(raw.replace(/\s+/g, " ").trim());
  const id = `ref-${index}`;
  if (!cleaned) {
    return { id, raw, parsed: false };
  }

  const doiMatch = DOI_RE.exec(cleaned);
  const doi = doiMatch?.[1]?.replace(/[.)\],;]+$/, "");

  let year: number | undefined;
  const yearMatches = [...cleaned.matchAll(new RegExp(YEAR_RE, "g"))];
  if (yearMatches.length) {
    const last = yearMatches[yearMatches.length - 1]!;
    year = Number(last[0]);
  }

  let journal: string | undefined;
  const jy = JOURNAL_YEAR_RE.exec(cleaned);
  if (jy) {
    const candidate = jy[1]!.replace(/\s+/g, " ").trim();
    // Avoid treating a long title fragment as journal
    if (candidate.length <= 60 && !/\bet al\b/i.test(candidate)) {
      journal = candidate.replace(/\.$/, "");
      if (!year && jy[2]) year = Number(jy[2]);
    }
  }

  // Authors often precede the first period if that segment is short and name-like
  let authorsLine: string | undefined;
  let titleLine: string | undefined;
  const firstDot = cleaned.indexOf(". ");
  if (firstDot > 0 && firstDot < 120) {
    const head = cleaned.slice(0, firstDot).trim();
    const rest = cleaned.slice(firstDot + 2).trim();
    const looksLikeAuthors =
      /^[A-Z]/.test(head) &&
      (head.includes(",") || /\s[A-Z]\.?$/.test(head) || /\bet al\b/i.test(head)) &&
      head.split(/\s+/).length <= 16;
    if (looksLikeAuthors) {
      authorsLine = head.length > 72 ? `${head.slice(0, 70)}…` : head;
      // Title: until next journal-ish segment
      const titleEnd = rest.search(/\.\s+[A-Z]/);
      const titleRaw = titleEnd > 20 ? rest.slice(0, titleEnd) : rest.split(/\.\s+\d{4}/)[0] ?? rest;
      titleLine = titleRaw.replace(/\.$/, "").trim();
      if (titleLine.length > 100) titleLine = `${titleLine.slice(0, 98)}…`;
    }
  }

  if (!authorsLine) {
    // Compact fallback preview
    titleLine = cleaned.length > 110 ? `${cleaned.slice(0, 108)}…` : cleaned;
  }

  const parsed = Boolean(authorsLine || journal || year || doi);

  return {
    id,
    raw: cleaned,
    authorsLine,
    titleLine,
    journal,
    year,
    doi,
    parsed,
  };
}

export function citationSearchBlob(c: CitationPreview): string {
  return [c.raw, c.authorsLine, c.titleLine, c.journal, c.year, c.doi]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

/** Split a References section body into citation lines. */
export function splitReferenceLines(blob: string): string[] {
  const text = blob.replace(/\r\n/g, "\n").trim();
  if (!text) return [];

  // Prefer numbered / bracketed entries
  const numbered = text.split(/\n(?=\s*(?:\[\d+\]|\d+\.)\s+)/);
  if (numbered.length > 1) {
    return numbered.map((l) => l.replace(/\s+/g, " ").trim()).filter(Boolean);
  }

  return text
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 12);
}

/** Numbered biblio lines wrongly promoted to Structure headings. */
export function looksLikeBibliographyHeading(heading: string, content?: string): boolean {
  const h = heading.trim();
  if (/^references?$/i.test(h)) return true;
  if (!/^(?:\[\d+\]|\d+\.)\s+\S/.test(h)) return false;
  // Citation text lives in the heading; body empty or tiny
  if (content && content.trim().length > 80) return false;
  return (
    h.length >= 24 ||
    /\bet al\b/i.test(h) ||
    YEAR_RE.test(h) ||
    DOI_RE.test(h) ||
    /,\s*[A-Z]\./.test(h)
  );
}
