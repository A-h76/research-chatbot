export type TocHeading = {
  id: string;
  text: string;
  level: 2 | 3;
};

/** Slugify heading text for on-this-page anchors (Mintlify TOC). */
export function slugifyHeading(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/[`*_~]/g, "")
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}

/** Extract ## / ### headings from markdown source (tests + SSR-friendly). */
export function extractToc(markdown: string): TocHeading[] {
  const out: TocHeading[] = [];
  const seen = new Map<string, number>();

  for (const line of markdown.split(/\r?\n/)) {
    const m = /^(#{2,3})\s+(.+?)\s*$/.exec(line);
    if (!m) continue;
    const level = m[1].length as 2 | 3;
    const text = m[2].replace(/#+$/, "").trim();
    if (!text) continue;
    let id = slugifyHeading(text);
    if (!id) continue;
    const n = seen.get(id) ?? 0;
    seen.set(id, n + 1);
    if (n > 0) id = `${id}-${n}`;
    out.push({ id, text, level });
  }

  return out;
}

/**
 * Assign stable ids to rendered h2/h3 and return TOC entries (DOM source of truth).
 */
export function applyHeadingIdsFromDom(root: HTMLElement): TocHeading[] {
  const out: TocHeading[] = [];
  const seen = new Map<string, number>();

  for (const el of Array.from(root.querySelectorAll("h2, h3"))) {
    const text = (el.textContent || "").trim();
    if (!text) continue;
    const level = el.tagName.toLowerCase() === "h2" ? 2 : 3;
    let id = slugifyHeading(text);
    if (!id) continue;
    const n = seen.get(id) ?? 0;
    seen.set(id, n + 1);
    if (n > 0) id = `${id}-${n}`;
    el.id = id;
    el.classList.add("scroll-mt-24");
    out.push({ id, text, level: level as 2 | 3 });
  }

  return out;
}
