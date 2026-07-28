import { useEffect, useRef, useState } from "react";
import { evidenceApi } from "../api";
import { mapExplainResponse } from "../services/evidenceMappers";
import type { ExplainResponse } from "../types";

export function useEvidenceExplain(opts: {
  documentId: number | null;
  projectId: number | null;
  selectedText: string;
  enabled?: boolean;
  refreshKey?: number;
}) {
  const { documentId, projectId, selectedText, enabled = true, refreshKey = 0 } = opts;
  const [result, setResult] = useState<ExplainResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled || documentId == null || projectId == null) return;
    const text = selectedText.trim();
    if (!text) return;

    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      setStatus("loading");
      setError(null);
      const rangeEnd = text.length;
      evidenceApi
        .explain({
          document_id: documentId,
          project_id: projectId,
          block_id: `sel_${hashText(text)}`,
          range_start: 0,
          range_end: rangeEnd,
          selected_text: text.slice(0, 2000),
        })
        .then((raw) => {
          setResult(mapExplainResponse(raw));
          setStatus("ok");
        })
        .catch((err) => {
          setStatus("error");
          setError(err instanceof Error ? err.message : "explain_failed");
        });
    }, 350);

    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [documentId, projectId, selectedText, enabled, refreshKey]);

  return { result, status, error };
}

function hashText(text: string): string {
  let h = 0;
  for (let i = 0; i < Math.min(text.length, 64); i += 1) {
    h = (h * 31 + text.charCodeAt(i)) >>> 0;
  }
  return h.toString(16);
}
