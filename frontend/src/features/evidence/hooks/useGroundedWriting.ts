import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "@/components/common/Toast";
import { ApiError } from "@/lib/apiClient";
import { evidenceApi } from "../api";

export type WritingSectionType =
  | "support_sentence"
  | "introduction"
  | "literature_review"
  | "discussion"
  | "clinical_summary"
  | "research_gap"
  | "executive_summary";

export const WRITING_SECTION_OPTIONS: Array<{
  value: WritingSectionType;
  label: string;
  experimental?: boolean;
}> = [
  { value: "literature_review", label: "Literature review" },
  { value: "support_sentence", label: "Support sentence", experimental: true },
  { value: "introduction", label: "Introduction", experimental: true },
  { value: "discussion", label: "Discussion", experimental: true },
  { value: "clinical_summary", label: "Clinical summary", experimental: true },
  { value: "research_gap", label: "Research gap", experimental: true },
  { value: "executive_summary", label: "Executive summary", experimental: true },
];

export type GroundedWritingBinding = {
  evidence_id: number;
  file_id?: number;
  page?: number | null;
  claim: string;
  quote: string;
  confidence_band?: string;
  study_type?: string;
};

export type GroundedWritingSection = {
  id: string;
  title: string;
  purpose?: string;
  paragraph: string | null;
  citations: Array<{
    evidence_id: number;
    file_id?: number;
    page?: number | null;
    claim: string;
    quote: string;
    confidence_band?: string;
  }>;
  evidence_ids: number[];
  bindings?: GroundedWritingBinding[];
  binding_count?: number;
  confidence: string;
  status: string;
  warnings?: string[];
};

export type WritingReview = {
  status: "pass" | "fail";
  pass_rate: number;
  sections_checked: number;
  sections_passed: number;
  issue_count: number;
  name?: string;
  metrics?: {
    grounding_pct: number;
    citation_coverage_pct: number;
    unsupported_claims: number;
  };
  issues: Array<{
    code: string;
    severity: string;
    section_id: string | null;
    message: string;
  }>;
};

export type WritingMetrics = {
  grounding_pct: number;
  citation_coverage: number;
  unsupported_sentence_rate: number;
  unsupported_claims?: number;
  paragraph_count: number;
  evidence_linked_paragraphs: number;
  unique_evidence_cited: number;
  supporting_count: number;
  reviewer_pass_rate?: number;
  reviewer_status?: string | null;
};

export type GroundedWritingResult = {
  status: "ok" | "blocked";
  blocked_reason: string | null;
  mode: string;
  section_type?: string;
  paragraph: string | null;
  sections?: GroundedWritingSection[];
  plan?: { section_type: string; slot_count: number; slots: Array<{ id: string; title: string }> };
  citations: Array<{
    evidence_id: number;
    file_id?: number;
    page?: number | null;
    claim: string;
    quote: string;
  }>;
  bibliography?: GroundedWritingBinding[];
  review?: WritingReview | null;
  warnings: string[];
  disclaimer: string;
  supporting_count?: number;
  metrics?: WritingMetrics | null;
  writing_version?: string;
};

function buildWritingQuery(opts: {
  projectId: number;
  documentId: number;
  selectedText: string;
  draftFallback?: string;
  sectionType?: WritingSectionType;
}) {
  const focus = (opts.selectedText || opts.draftFallback || "").trim().slice(0, 2000);
  return {
    intent: "support_sentence",
    section_type: opts.sectionType || "support_sentence",
    scope: {
      project_id: opts.projectId,
      document_id: opts.documentId,
    },
    filters: {
      status: ["accepted", "candidate"],
      require_page_anchor: true,
    },
    ranking_strategy: "default_v0",
    result_limit: 20,
    query_text: focus,
    anchors: {
      block_id: focus ? `sel_${hashText(focus)}` : "draft",
      selected_text: focus,
    },
  };
}

function hashText(text: string): string {
  let h = 0;
  for (let i = 0; i < Math.min(text.length, 64); i += 1) {
    h = (h * 31 + text.charCodeAt(i)) >>> 0;
  }
  return h.toString(16);
}

export function useGroundedWriting() {
  const [last, setLast] = useState<GroundedWritingResult | null>(null);

  const mutation = useMutation({
    mutationFn: async (opts: {
      projectId: number;
      documentId: number;
      selectedText: string;
      draftFallback?: string;
      sectionType?: WritingSectionType;
    }) => {
      const query = buildWritingQuery(opts);
      const raw = await evidenceApi.writing(query);
      const writing = raw.writing;
      if (!writing) {
        throw new Error("writing_payload_missing");
      }
      return {
        ...(writing as GroundedWritingResult),
        writing_version: raw.writing_version,
      };
    },
    onSuccess: (writing) => {
      setLast(writing);
      if (writing.status === "blocked") {
        toast.error(
          writing.blocked_reason === "opposed_evidence"
            ? "Generation blocked: only contradicting evidence"
            : "Generation blocked: insufficient supporting evidence",
        );
        return;
      }
      const n = writing.sections?.filter((s) => s.status === "ok").length ?? 1;
      const reviewFail = writing.review?.status === "fail";
      toast.success(
        reviewFail
          ? `Draft ready with reviewer issues (${n} sections) — verify bindings before export`
          : n > 1
            ? `Grounded literature draft ready (${n} sections) — verify evidence before inserting`
            : "Grounded draft ready — review citations before inserting",
      );
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        toast.error(err.message || "Grounded generate failed");
        return;
      }
      toast.error(err instanceof Error ? err.message : "Grounded generate failed");
    },
  });

  return {
    generate: mutation.mutate,
    generateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    last,
    clear: () => setLast(null),
  };
}
