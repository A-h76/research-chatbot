/**
 * Literature Review Markdown export (Sprint C).
 * Body + Evidence Appendix + Bibliography + Generation metadata.
 */

import type {
  GroundedWritingBinding,
  GroundedWritingResult,
} from "@/features/evidence/hooks/useGroundedWriting";

export type GroundedExportSnapshot = {
  documentId: number;
  title: string;
  body: string;
  writing: GroundedWritingResult;
  writing_version?: string;
  savedAt: string;
};

const STORAGE_PREFIX = "dhund:grounded_export:";

export function groundedExportStorageKey(documentId: number): string {
  return `${STORAGE_PREFIX}${documentId}`;
}

export function saveGroundedExportSnapshot(snapshot: GroundedExportSnapshot): void {
  try {
    sessionStorage.setItem(
      groundedExportStorageKey(snapshot.documentId),
      JSON.stringify(snapshot),
    );
  } catch {
    // ignore quota / private mode
  }
}

export function loadGroundedExportSnapshot(
  documentId: number,
): GroundedExportSnapshot | null {
  try {
    const raw = sessionStorage.getItem(groundedExportStorageKey(documentId));
    if (!raw) return null;
    return JSON.parse(raw) as GroundedExportSnapshot;
  } catch {
    return null;
  }
}

function pct(value: unknown): string {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "n/a";
  return `${Math.round(n * 100)}%`;
}

function bindingsFromWriting(writing: GroundedWritingResult): GroundedWritingBinding[] {
  if (writing.bibliography?.length) return writing.bibliography;
  const seen = new Set<number>();
  const flat: GroundedWritingBinding[] = [];
  for (const sec of writing.sections || []) {
    for (const b of sec.bindings || []) {
      if (seen.has(b.evidence_id)) continue;
      seen.add(b.evidence_id);
      flat.push(b);
    }
  }
  if (flat.length) return flat;
  for (const c of writing.citations || []) {
    if (seen.has(c.evidence_id)) continue;
    seen.add(c.evidence_id);
    flat.push({
      evidence_id: c.evidence_id,
      file_id: c.file_id,
      page: c.page,
      claim: c.claim,
      quote: c.quote,
    });
  }
  return flat;
}

export function computeExportTraceability(writing: GroundedWritingResult): {
  paragraph_count: number;
  paragraphs_with_evidence: number;
  traceability_pct: number;
  meets_100: boolean;
} {
  const sections = (writing.sections || []).filter(
    (s) => s.status === "ok" && (s.paragraph || "").trim(),
  );
  if (!sections.length && (writing.paragraph || "").trim()) {
    const ok = bindingsFromWriting(writing).length >= 1;
    return {
      paragraph_count: 1,
      paragraphs_with_evidence: ok ? 1 : 0,
      traceability_pct: ok ? 1 : 0,
      meets_100: ok,
    };
  }
  // Match backend export_markdown: linked only if bindings/ids present AND no orphans.
  const linked = sections.filter(
    (s) =>
      (s.bindings?.length || s.evidence_ids?.length || 0) > 0 &&
      !(s.orphan_ids && s.orphan_ids.length > 0),
  ).length;
  const total = sections.length;
  const pctVal = total ? linked / total : 0;
  return {
    paragraph_count: total,
    paragraphs_with_evidence: linked,
    traceability_pct: pctVal,
    meets_100: total > 0 && linked === total,
  };
}

/** True when any Research Reviewer issue has severity=error (B-514). */
export function reviewHasSeverityError(
  review: GroundedWritingResult["review"] | null | undefined,
): boolean {
  return (review?.issues || []).some(
    (i) => String(i.severity || "").toLowerCase() === "error",
  );
}

/** V1: refuse lit-review export when grounding bar is not met. */
export function canExportGroundedLitReview(writing: GroundedWritingResult | null | undefined): {
  ok: boolean;
  reason?: string;
} {
  if (!writing) {
    return { ok: false, reason: "No grounded export snapshot — generate and accept a review first" };
  }
  if (writing.status === "blocked") {
    return { ok: false, reason: "Draft is blocked — insufficient evidence" };
  }
  if (writing.accept_allowed === false) {
    return {
      ok: false,
      reason: "Research Reviewer blocked Accept/export — revise unbound or unsupported claims",
    };
  }
  if (reviewHasSeverityError(writing.review)) {
    return {
      ok: false,
      reason: "Research Reviewer has error-severity findings — fix before export",
    };
  }
  if (writing.review?.status === "fail") {
    return { ok: false, reason: "Research Reviewer failed — fix issues before export" };
  }
  const trace = computeExportTraceability(writing);
  if (!trace.meets_100) {
    return { ok: false, reason: "Evidence traceability below 100% — every section needs bindings" };
  }
  return { ok: true };
}

export function buildLiteratureReviewMarkdown(opts: {
  title: string;
  body: string;
  writing?: GroundedWritingResult | null;
  writing_version?: string;
  exported_at?: string;
}): string {
  const writing = opts.writing || null;
  const when = opts.exported_at || new Date().toISOString();
  const bindings = writing ? bindingsFromWriting(writing) : [];
  const trace = writing
    ? computeExportTraceability(writing)
    : {
        paragraph_count: 0,
        paragraphs_with_evidence: 0,
        traceability_pct: 0,
        meets_100: false,
      };
  const metrics = writing?.metrics;
  const review = writing?.review;

  const lines: string[] = [
    `# ${(opts.title || "Literature review").trim()}`,
    "",
    "## Literature review",
    "",
    (opts.body || "").trim() || "_No draft body._",
    "",
    "## Evidence appendix",
    "",
  ];

  if (!bindings.length) {
    lines.push("_No EvidenceObject bindings available for this export._", "");
  } else {
    for (const b of bindings) {
      lines.push(`### Evidence #${b.evidence_id}`);
      const meta: string[] = [];
      if (b.page != null) meta.push(`page ${b.page}`);
      if (b.confidence_band) meta.push(b.confidence_band);
      if (b.study_type) meta.push(b.study_type);
      if (meta.length) lines.push(`- Provenance: ${meta.join(", ")}`);
      if (b.claim) lines.push(`- Claim: ${b.claim}`);
      if (b.quote) lines.push(`- Quote: “${b.quote}”`);
      lines.push("");
    }
  }

  lines.push("## Bibliography", "");
  if (!bindings.length) {
    lines.push("_Empty bibliography._", "");
  } else {
    bindings.forEach((b, i) => {
      const title = (b.paper_title || "").trim();
      const authors = (b.authors || "").trim();
      const year = (b.year || "").trim();
      const venue = (b.venue || "").trim();
      const doi = (b.doi || "").trim();
      const claim = (b.claim || "").trim();
      const pageBit = b.page != null ? ` (p. ${b.page})` : "";
      if (title || authors) {
        const bits = [
          authors || null,
          year ? `(${year})` : null,
          title || null,
          venue || null,
          doi ? `https://doi.org/${doi}` : null,
          `[#${b.evidence_id}]${pageBit}`,
        ].filter(Boolean);
        lines.push(`${i + 1}. ${bits.join(". ")}`);
      } else {
        lines.push(
          `${i + 1}. [#${b.evidence_id}] ${claim || "(no claim text)"}${pageBit}`,
        );
      }
    });
    lines.push("");
  }

  lines.push(
    "## Generation metadata",
    "",
    `- exported_at: ${when}`,
    `- writing_version: ${opts.writing_version || "unknown"}`,
    `- mode: ${writing?.mode || "unknown"}`,
    `- section_type: ${writing?.section_type || "unknown"}`,
    `- status: ${writing?.status || "unknown"}`,
    `- grounding_pct: ${pct(metrics?.grounding_pct ?? review?.metrics?.grounding_pct)}`,
    `- citation_coverage: ${pct(metrics?.citation_coverage ?? review?.metrics?.citation_coverage_pct)}`,
    `- unsupported_claims: ${metrics?.unsupported_claims ?? review?.metrics?.unsupported_claims ?? "n/a"}`,
    `- research_reviewer: ${review?.status || "n/a"} (pass_rate=${pct(review?.pass_rate)})`,
    `- reviewer_version: ${review?.reviewer_version || "n/a"}`,
    `- reviewer_issue_count: ${review?.issue_count ?? review?.issues?.length ?? "n/a"}`,
    `- evidence_traceability_pct: ${pct(trace.traceability_pct)}`,
    `- evidence_traceability_100: ${trace.meets_100 ? "yes" : "no"}`,
    `- unique_evidence_cited: ${metrics?.unique_evidence_cited ?? bindings.length}`,
    `- disclaimer: ${(writing?.disclaimer || "").trim()}`,
    "",
  );

  return `${lines.join("\n").trimEnd()}\n`;
}

/** Phase A.4: BibTeX from Evidence → Paper metadata (never invent literature). */
export function buildBibtexFromWriting(writing: GroundedWritingResult | null | undefined): string {
  const bindings = writing ? bindingsFromWriting(writing) : [];
  if (!bindings.length) return "";

  const seenFiles = new Set<number>();
  const entries: string[] = [];

  for (const b of bindings) {
    const fid = b.file_id != null ? Number(b.file_id) : null;
    if (fid != null) {
      if (seenFiles.has(fid)) continue;
      seenFiles.add(fid);
    }
    const authors = (b.authors || "").trim() || "Unknown";
    const title = (b.paper_title || "").trim() || `Evidence ${b.evidence_id}`;
    const year = (b.year || "").trim() || "nd";
    const venue = (b.venue || "").trim();
    const doi = (b.doi || "").trim();
    const firstAuthor = authors.split(";")[0]?.split(",")[0]?.trim() || "anon";
    const keyBase = firstAuthor.replace(/[^a-zA-Z0-9]/g, "").toLowerCase() || "ref";
    const key = `${keyBase}${year === "nd" ? "" : year}_e${b.evidence_id}`;

    const fields: string[] = [
      `  author = {${authors.replace(/;/g, " and ")}}`,
      `  title = {${title}}`,
      `  year = {${year}}`,
    ];
    if (venue) fields.push(`  journal = {${venue}}`);
    if (doi) fields.push(`  doi = {${doi}}`);
    fields.push(`  note = {Dhund evidence #${b.evidence_id}}`);
    entries.push(`@article{${key},\n${fields.join(",\n")}\n}`);
  }

  return `${entries.join("\n\n")}\n`;
}

export function downloadTextFile(
  filename: string,
  content: string,
  mime = "text/plain;charset=utf-8",
): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadMarkdownFile(filename: string, markdown: string): void {
  downloadTextFile(
    filename.endsWith(".md") ? filename : `${filename}.md`,
    markdown,
    "text/markdown;charset=utf-8",
  );
}
