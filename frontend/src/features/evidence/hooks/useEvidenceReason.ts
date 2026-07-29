import { useEffect, useRef, useState } from "react";
import { evidenceApi } from "../api";

export type ReasonEnvelope = {
  reasoning?: {
    summary_code: string;
    sufficiency: string;
    steps: Array<{ step: string; detail: string; code?: string }>;
    evidence_ids: number[];
    mediator_labels: string[];
  };
  consensus?: {
    label?: string;
    supporting?: number;
    contradicting?: number;
    neutral?: number;
  };
  conflict?: {
    has_conflict?: boolean;
    mediators?: string[];
  };
};

function buildQuery(opts: {
  projectId: number;
  documentId: number;
  selectedText: string;
}) {
  const text = opts.selectedText.trim().slice(0, 2000);
  return {
    intent: "support_sentence",
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
    query_text: text,
    anchors: {
      block_id: text ? `sel_${hashText(text)}` : "blk",
      selected_text: text,
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

/** Debounced RI reason stage for Inspector enrichment. */
export function useEvidenceReason(opts: {
  documentId: number | null;
  projectId: number | null;
  selectedText: string;
  enabled?: boolean;
  refreshKey?: number;
}) {
  const { documentId, projectId, selectedText, enabled = true, refreshKey = 0 } = opts;
  const [result, setResult] = useState<ReasonEnvelope | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled || documentId == null || projectId == null) return;
    const text = selectedText.trim();
    if (!text) {
      setResult(null);
      setStatus("idle");
      return;
    }

    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      setStatus("loading");
      evidenceApi
        .reason(buildQuery({ projectId, documentId, selectedText: text }))
        .then((raw) => {
          setResult(raw as ReasonEnvelope);
          setStatus("ok");
        })
        .catch(() => {
          setStatus("error");
          setResult(null);
        });
    }, 450);

    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [documentId, projectId, selectedText, enabled, refreshKey]);

  return { result, status };
}
