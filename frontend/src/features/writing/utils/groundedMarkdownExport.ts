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
  const linked = sections.filter(
    (s) => (s.bindings?.length || s.evidence_ids?.length || 0) > 0,
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
      const claim = (b.claim || "").trim() || "(no claim text)";
      const pageBit = b.page != null ? `, page ${b.page}` : "";
      lines.push(`${i + 1}. [#${b.evidence_id}] ${claim}${pageBit}`);
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
    `- evidence_traceability_pct: ${pct(trace.traceability_pct)}`,
    `- evidence_traceability_100: ${trace.meets_100 ? "yes" : "no"}`,
    `- unique_evidence_cited: ${metrics?.unique_evidence_cited ?? bindings.length}`,
    `- disclaimer: ${(writing?.disclaimer || "").trim()}`,
    "",
  );

  return `${lines.join("\n").trimEnd()}\n`;
}

export function downloadMarkdownFile(filename: string, markdown: string): void {
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".md") ? filename : `${filename}.md`;
  a.click();
  URL.revokeObjectURL(url);
}
