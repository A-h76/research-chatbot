import { useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "@/components/common/Toast";
import { formatApiFailure } from "@/lib/apiErrors";
import { evidenceApi } from "../api";
import { trackWorkflowEvent } from "@/lib/workflowTelemetry";

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
  { value: "introduction", label: "Background / introduction" },
  { value: "discussion", label: "Discussion" },
  { value: "support_sentence", label: "Support sentence", experimental: true },
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
  paper_title?: string;
  authors?: string;
  year?: string;
  venue?: string;
  doi?: string;
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
  orphan_ids?: number[];
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
  reviewer_version?: string;
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
    evidence_ids?: number[];
    finding_id?: number;
    status?: string;
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
  /** False when Reviewer error codes block Accept/export (draft may still be inspectable). */
  accept_allowed?: boolean;
  mode: string;
  section_type?: string;
  paragraph: string | null;
  sections?: GroundedWritingSection[];
  plan?: { section_type: string; slot_count: number; slots: Array<{ id: string; title: string }> };
  /** RI-009 theme-aware outline (slot → themes/evidence/papers). */
  outline?: Array<{
    slot_id?: string;
    title?: string;
    purpose?: string;
    facet?: string;
    theme_ids?: string[];
    evidence_ids?: number[];
    paper_ids?: number[];
  }>;
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
  /** Reproducible draft provenance. */
  draft_metadata?: {
    evidence_ids?: number[];
    theme_ids?: string[];
    gap_ids?: string[];
    paper_ids?: number[];
    consensus_label?: string;
    product_label?: string;
    consensus_version?: string | null;
    conflict_version?: string | null;
    writing_version?: string;
    ri_depth_version?: string;
    themes_fingerprint?: string;
    prompt_version?: string;
    reproducibility_hash?: string;
    ai_execution?: Record<string, unknown>;
  };
  /** Capability Router provenance (ADR-0016) when writing used the gateway. */
  ai_execution?: {
    research_job?: string;
    capability?: string;
    execution_policy?: string;
    provider?: string;
    model?: string;
    prompt_version?: string;
    router_version?: string;
    execution_id?: string;
  };
  /** RI-009 — themes/gaps/methods/timeline/consensus depth that informed the draft. */
  ri_context?: {
    ri_depth_version?: string;
    themes?: Array<{
      id?: string;
      label?: string;
      key_terms?: string[];
      evidence_ids?: number[];
      size?: number;
    }>;
    gaps?: Array<{
      id?: string;
      type?: string;
      statement?: string;
      suggested_questions?: string[];
      evidence_ids?: number[];
    }>;
    methodology?: {
      cards?: Array<{ id?: string; kind?: string; title?: string; advice?: string }>;
      design_counts?: Record<string, number>;
    };
    timeline?: {
      span?: { start_year?: number | null; end_year?: number | null };
      entries?: Array<{ year?: number; evidence_count?: number }>;
    };
    consensus?: {
      label?: string;
      product_label?: string;
      supporting_ids?: number[];
      contradicting_ids?: number[];
    };
    conflict?: {
      has_conflict?: boolean;
      mediators?: string[];
      product_summary?: string | null;
    };
    metrics?: {
      theme_count?: number;
      gap_count?: number;
      object_count?: number;
    };
  };
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
      // Phase A.3: draft context = accepted evidence only
      status: ["accepted"],
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
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const generateCountRef = useRef(0);

  const mutation = useMutation({
    mutationFn: async (opts: {
      projectId: number;
      documentId: number;
      selectedText: string;
      draftFallback?: string;
      sectionType?: WritingSectionType;
    }) => {
      const query = buildWritingQuery(opts);
      const sectionType = opts.sectionType || "support_sentence";
      setJobStatus(null);

      // W6 — long literature reviews go through the research job queue.
      if (sectionType === "literature_review") {
        setJobStatus("Queuing literature_review job…");
        const enqueued = await evidenceApi.enqueueResearchJob(opts.projectId, {
          type: "literature_review",
          query,
        });
        let writingPayload: Record<string, unknown> | undefined;
        let writingVersion: string | undefined;
        if (enqueued.status === "done" && enqueued.result) {
          const r = enqueued.result as {
            writing?: GroundedWritingResult;
            writing_version?: string;
          };
          writingPayload = r.writing as unknown as Record<string, unknown>;
          writingVersion = r.writing_version;
        } else if (enqueued.job_id) {
          let done: Awaited<ReturnType<typeof evidenceApi.researchJob>> | null = null;
          for (let i = 0; i < 20; i += 1) {
            setJobStatus(`Waiting on research job… (${i + 1}/20)`);
            await new Promise((r) => setTimeout(r, 1500));
            const st = await evidenceApi.researchJob(enqueued.job_id!);
            if (st.status === "done") {
              done = st;
              break;
            }
            if (st.status === "failed") {
              throw new Error(st.last_error || "literature_review_failed");
            }
          }
          if (!done?.result) {
            // Worker may be offline — fall back to sync path.
            toast.message("Worker slow — finishing literature review inline");
            setJobStatus("Finishing inline…");
            const raw = await evidenceApi.writing(query);
            const writing = raw.writing;
            if (!writing) throw new Error("writing_payload_missing");
            return {
              ...(writing as GroundedWritingResult),
              writing_version: raw.writing_version,
              section_type: sectionType,
              _projectId: opts.projectId,
              _documentId: opts.documentId,
            };
          }
          const r = done.result as {
            writing?: GroundedWritingResult;
            writing_version?: string;
          };
          writingPayload = r.writing as unknown as Record<string, unknown>;
          writingVersion = r.writing_version;
        } else {
          setJobStatus("Generating section…");
          const raw = await evidenceApi.writing(query);
          const writing = raw.writing;
          if (!writing) throw new Error("writing_payload_missing");
          return {
            ...(writing as GroundedWritingResult),
            writing_version: raw.writing_version,
            section_type: sectionType,
            _projectId: opts.projectId,
            _documentId: opts.documentId,
          };
        }
        if (!writingPayload) throw new Error("writing_payload_missing");
        return {
          ...(writingPayload as GroundedWritingResult),
          writing_version: writingVersion,
          section_type: sectionType,
          _projectId: opts.projectId,
          _documentId: opts.documentId,
        };
      }

      setJobStatus("Generating section…");
      const raw = await evidenceApi.writing(query);
      const writing = raw.writing;
      if (!writing) {
        throw new Error("writing_payload_missing");
      }
      return {
        ...(writing as GroundedWritingResult),
        writing_version: raw.writing_version,
        section_type: sectionType,
        _projectId: opts.projectId,
        _documentId: opts.documentId,
      };
    },
    onSuccess: (writing) => {
      setJobStatus(null);
      setLast(writing);
      generateCountRef.current += 1;
      const projectId = (writing as { _projectId?: number })._projectId;
      const documentId = (writing as { _documentId?: number })._documentId;
      trackWorkflowEvent(
        generateCountRef.current > 1 ? "draft_regenerated" : "draft_generated",
        {
          projectId,
          meta: {
            status: writing.status,
            section_type: writing.section_type,
            document_id: documentId,
            citation_count: writing.citations?.length ?? 0,
          },
        },
      );
      if (writing.review) {
        trackWorkflowEvent("reviewer_opened", {
          projectId,
          meta: {
            status: writing.review.status,
            issue_count: writing.review.issue_count,
          },
        });
      }
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
      setJobStatus(null);
      toast.error(formatApiFailure(err, "Grounded generate failed"));
    },
  });

  return {
    generate: mutation.mutate,
    generateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    jobStatus,
    last,
    clear: () => setLast(null),
  };
}
