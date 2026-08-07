/** Markdown-ish wraps for the Writing Studio manuscript textarea. */

export type HeadingLevel = "p" | "h1" | "h2" | "h3";

export function wrapSelection(
  content: string,
  start: number,
  end: number,
  before: string,
  after: string,
): { content: string; selectionStart: number; selectionEnd: number } {
  const s = Math.max(0, Math.min(start, content.length));
  const e = Math.max(s, Math.min(end, content.length));
  const selected = content.slice(s, e) || "text";
  const next = `${content.slice(0, s)}${before}${selected}${after}${content.slice(e)}`;
  const selectionStart = s + before.length;
  const selectionEnd = selectionStart + selected.length;
  return { content: next, selectionStart, selectionEnd };
}

export function toggleInlineMark(
  content: string,
  start: number,
  end: number,
  mark: "**" | "*" | "__",
): { content: string; selectionStart: number; selectionEnd: number } {
  return wrapSelection(content, start, end, mark, mark);
}

/** Apply heading to the line containing the caret (or selection). */
export function applyHeadingToLine(
  content: string,
  start: number,
  end: number,
  level: HeadingLevel,
): { content: string; selectionStart: number; selectionEnd: number } {
  const lineStart = content.lastIndexOf("\n", Math.max(0, start - 1)) + 1;
  let lineEnd = content.indexOf("\n", end);
  if (lineEnd < 0) lineEnd = content.length;
  const line = content.slice(lineStart, lineEnd);
  const stripped = line.replace(/^#{1,6}\s+/, "");
  const prefix =
    level === "h1" ? "# " : level === "h2" ? "## " : level === "h3" ? "### " : "";
  const nextLine = `${prefix}${stripped}`;
  const next = `${content.slice(0, lineStart)}${nextLine}${content.slice(lineEnd)}`;
  const caret = lineStart + nextLine.length;
  return { content: next, selectionStart: caret, selectionEnd: caret };
}

export function applyBulletList(
  content: string,
  start: number,
  end: number,
): { content: string; selectionStart: number; selectionEnd: number } {
  const lineStart = content.lastIndexOf("\n", Math.max(0, start - 1)) + 1;
  let lineEnd = content.indexOf("\n", end);
  if (lineEnd < 0) lineEnd = content.length;
  const block = content.slice(lineStart, lineEnd);
  const nextBlock = block
    .split("\n")
    .map((line) => {
      const t = line.replace(/^#{1,6}\s+/, "").replace(/^[-*]\s+/, "").replace(/^\d+\.\s+/, "");
      return `- ${t || "item"}`;
    })
    .join("\n");
  const next = `${content.slice(0, lineStart)}${nextBlock}${content.slice(lineEnd)}`;
  return {
    content: next,
    selectionStart: lineStart,
    selectionEnd: lineStart + nextBlock.length,
  };
}

export function applyNumberedList(
  content: string,
  start: number,
  end: number,
): { content: string; selectionStart: number; selectionEnd: number } {
  const lineStart = content.lastIndexOf("\n", Math.max(0, start - 1)) + 1;
  let lineEnd = content.indexOf("\n", end);
  if (lineEnd < 0) lineEnd = content.length;
  const block = content.slice(lineStart, lineEnd);
  const nextBlock = block
    .split("\n")
    .map((line, i) => {
      const t = line.replace(/^#{1,6}\s+/, "").replace(/^[-*]\s+/, "").replace(/^\d+\.\s+/, "");
      return `${i + 1}. ${t || "item"}`;
    })
    .join("\n");
  const next = `${content.slice(0, lineStart)}${nextBlock}${content.slice(lineEnd)}`;
  return {
    content: next,
    selectionStart: lineStart,
    selectionEnd: lineStart + nextBlock.length,
  };
}

export function applyLink(
  content: string,
  start: number,
  end: number,
): { content: string; selectionStart: number; selectionEnd: number } {
  const s = Math.max(0, Math.min(start, content.length));
  const e = Math.max(s, Math.min(end, content.length));
  const selected = content.slice(s, e) || "link text";
  const inserted = `[${selected}](https://)`;
  const next = `${content.slice(0, s)}${inserted}${content.slice(e)}`;
  const urlStart = s + selected.length + 3;
  return { content: next, selectionStart: urlStart, selectionEnd: urlStart + 8 };
}

/** Wrap selection in a colored span (stored inline HTML; rendered in overlay). */
export function applyTextColor(
  content: string,
  start: number,
  end: number,
  color: string,
): { content: string; selectionStart: number; selectionEnd: number } {
  const before = `<span style="color:${color}">`;
  const after = "</span>";
  return wrapSelection(content, start, end, before, after);
}

export function detectHeadingLevel(content: string, caret: number): HeadingLevel {
  const lineStart = content.lastIndexOf("\n", Math.max(0, caret - 1)) + 1;
  let lineEnd = content.indexOf("\n", caret);
  if (lineEnd < 0) lineEnd = content.length;
  const line = content.slice(lineStart, lineEnd);
  if (/^#\s+/.test(line)) return "h1";
  if (/^##\s+/.test(line)) return "h2";
  if (/^###\s+/.test(line)) return "h3";
  return "p";
}
