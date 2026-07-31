/**
 * Light formatting for Structure-tab section bodies.
 * Extraction often embeds labels (Keywords:, spaced "a b s t r a c t") as plain lines
 * and soft-wraps prose to a narrow PDF column — we reflow that to full-width paragraphs.
 */

const LABEL_HEADING =
  /^(keywords?|abstract|introduction|background|methods?|materials?\s+and\s+methods|results?|discussion|conclusion|conclusions|references|acknowledgements?|acknowledgment|funding|conflicts?\s+of\s+interest|supplementary|appendix)\s*:?\s*$/i;

const INLINE_LABEL = /^(keywords?|abstract)\s*:\s*(.*)$/i;

/** Common English suffixes that often land alone after a mid-word PDF wrap. */
const MIDWORD_SUFFIX =
  /^(tion|sion|tation|ment|ings?|ness|ity|ities|ies|ous|ive|ally|ence|ance|ation|ified|cations?)$/i;

/** Spaced letter headings from PDF layout, e.g. "a b s t r a c t". */
export function isSpacedLetterHeading(line: string): boolean {
  const parts = line.trim().split(/\s+/);
  if (parts.length < 4) return false;
  return parts.every((p) => /^[A-Za-z]$/.test(p));
}

export function displayHeadingLabel(line: string): string {
  const t = line.trim();
  if (isSpacedLetterHeading(t)) {
    const joined = t.replace(/\s+/g, "");
    return joined.charAt(0).toUpperCase() + joined.slice(1).toLowerCase();
  }
  const inline = INLINE_LABEL.exec(t);
  if (inline) {
    const label = inline[1]!;
    return label.charAt(0).toUpperCase() + label.slice(1).toLowerCase();
  }
  return t.replace(/:$/, "");
}

export function isSectionBodyHeading(line: string): boolean {
  const t = line.trim();
  if (!t) return false;
  if (isSpacedLetterHeading(t)) return true;
  if (LABEL_HEADING.test(t)) return true;
  if (INLINE_LABEL.test(t) && t.length < 100) return true;
  // Short all-caps labels (PDF noise headings)
  if (
    t.length <= 48 &&
    /[A-Z]/.test(t) &&
    !/[a-z]/.test(t) &&
    t.split(/\s+/).length <= 8 &&
    !/^\d+$/.test(t)
  ) {
    return true;
  }
  // Numbered section titles that appear inside body text
  if (/^\d+(\.\d+)*\.?\s+[A-Za-z]/.test(t) && t.length < 90 && !/[.!?]$/.test(t)) {
    return true;
  }
  return false;
}

export type SectionBodyBlock =
  | { kind: "heading"; label: string; rest?: string }
  | { kind: "paragraph"; text: string };

/**
 * Join PDF soft-wrapped lines into one flowing paragraph.
 * Blank lines are handled by the caller (paragraph breaks).
 */
export function unwrapSoftWrappedLines(chunkLines: string[]): string {
  const lines = chunkLines.map((l) => l.trim()).filter((l) => l.length > 0);
  if (!lines.length) return "";

  let out = lines[0]!;
  for (let i = 1; i < lines.length; i++) {
    const next = lines[i]!;
    if (/[A-Za-z]-$/.test(out)) {
      // "detoxifi-" + "cation" → "detoxification"
      out = out.slice(0, -1) + next;
      continue;
    }

    const lastWord = out.split(/\s+/).pop() ?? "";
    const firstToken = next.match(/^[A-Za-z]+/)?.[0] ?? "";
    // Only glue when the next token is a clear wrap suffix (…|cation), not normal words (for, the, …).
    const joinMidWord =
      /^[A-Za-z]{3,}$/.test(lastWord) &&
      /^[a-z]/.test(next) &&
      firstToken.length > 0 &&
      MIDWORD_SUFFIX.test(firstToken) &&
      !/[.!?…:;,"”')\]]$/.test(out);

    if (joinMidWord) {
      const rest = next.slice(firstToken.length).replace(/^\s+/, "");
      if (rest && /^[,.;:!?)\]”']/.test(rest)) {
        out = out + firstToken + rest;
      } else if (rest) {
        out = `${out}${firstToken} ${rest}`;
      } else {
        out = out + firstToken;
      }
      continue;
    }

    out = `${out} ${next}`;
  }

  return out.replace(/\s{2,}/g, " ").trim();
}

/** Split raw section text into heading / full-width paragraph blocks. */
export function parseSectionBody(content: string): SectionBodyBlock[] {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: SectionBodyBlock[] = [];
  let para: string[] = [];

  const flushPara = () => {
    const text = unwrapSoftWrappedLines(para);
    para = [];
    if (text) blocks.push({ kind: "paragraph", text });
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      flushPara();
      continue;
    }
    if (isSectionBodyHeading(trimmed)) {
      flushPara();
      const inline = INLINE_LABEL.exec(trimmed);
      if (inline && inline[2]?.trim()) {
        blocks.push({
          kind: "heading",
          label: displayHeadingLabel(trimmed),
          rest: inline[2].trim(),
        });
      } else {
        blocks.push({ kind: "heading", label: displayHeadingLabel(trimmed) });
      }
      continue;
    }
    para.push(line);
  }
  flushPara();
  return blocks;
}
