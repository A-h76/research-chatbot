/** Pure helpers for inserting / replacing / removing [#id] cites in manuscript text. */

export const EVIDENCE_MARKER_RE = /\[#(\d+)\]/g;

export function insertAtCaret(
  content: string,
  insertText: string,
  selectionStart: number,
  selectionEnd: number,
): { content: string; caret: number } {
  const start = Math.max(0, Math.min(selectionStart, content.length));
  const end = Math.max(start, Math.min(selectionEnd, content.length));
  const before = content.slice(0, start);
  const after = content.slice(end);
  const needsSpaceBefore = Boolean(before && !/\s$/.test(before) && !insertText.startsWith(" "));
  const needsSpaceAfter = Boolean(after && !/^\s/.test(after) && !insertText.endsWith(" "));
  const chunk = `${needsSpaceBefore ? " " : ""}${insertText}${needsSpaceAfter ? " " : ""}`;
  const next = `${before}${chunk}${after}`;
  return { content: next, caret: before.length + chunk.length };
}

export function replaceSelection(
  content: string,
  insertText: string,
  selectionStart: number,
  selectionEnd: number,
): { content: string; caret: number } {
  return insertAtCaret(content, insertText, selectionStart, selectionEnd);
}

/** If selection is exactly one [#id] marker (with optional surrounding spaces), return id. */
export function selectedEvidenceMarkerId(
  content: string,
  selectionStart: number,
  selectionEnd: number,
): number | null {
  const selected = content.slice(selectionStart, selectionEnd).trim();
  const m = /^\[#(\d+)\]$/.exec(selected);
  if (m) return Number(m[1]);
  // Expand to nearest marker if caret inside [#123]
  const left = content.lastIndexOf("[#", selectionStart);
  if (left < 0) return null;
  const right = content.indexOf("]", left);
  if (right < 0 || right < selectionStart) return null;
  const token = content.slice(left, right + 1);
  const m2 = /^\[#(\d+)\]$/.exec(token);
  if (!m2) return null;
  if (selectionStart >= left && selectionEnd <= right + 1) return Number(m2[1]);
  return null;
}

export function removeEvidenceMarker(
  content: string,
  evidenceId: number,
): { content: string; removed: number } {
  const re = new RegExp(`\\s*\\[#${evidenceId}\\]`, "g");
  let removed = 0;
  const next = content.replace(re, () => {
    removed += 1;
    return "";
  });
  return { content: next.replace(/  +/g, " ").replace(/\n{3,}/g, "\n\n"), removed };
}

export function markerPreviewLabel(evidenceId: number, claim?: string): string {
  const c = (claim || "").trim();
  return c ? `Evidence #${evidenceId}: ${c.slice(0, 120)}` : `Evidence #${evidenceId}`;
}
