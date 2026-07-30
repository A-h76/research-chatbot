/**
 * Phase A.6 — workflow instrumentation (FE).
 * Fire-and-forget; never send manuscript / quote / claim bodies.
 */
import { api } from "@/lib/apiClient";

export type WorkflowEventName =
  | "project_created"
  | "papers_uploaded"
  | "evidence_extracted"
  | "evidence_accepted"
  | "evidence_rejected"
  | "decision_recorded"
  | "draft_generated"
  | "draft_regenerated"
  | "reviewer_opened"
  | "export_completed"
  | "workflow_abandoned"
  | "analysis_view_opened";

type Meta = Record<string, string | number | boolean | null | undefined>;

const SENSITIVE = new Set([
  "quote",
  "claim",
  "selected_text",
  "content",
  "body",
  "paragraph",
  "manuscript",
]);

export function trackWorkflowEvent(
  event: WorkflowEventName,
  opts?: { projectId?: number | null; meta?: Meta },
): void {
  const meta: Record<string, string | number | boolean | null> = {};
  for (const [k, v] of Object.entries(opts?.meta || {})) {
    if (SENSITIVE.has(k)) continue;
    if (v === undefined) continue;
    meta[k] = v;
  }

  // Local mirror for writing-desk listeners / debug
  window.dispatchEvent(
    new CustomEvent("dhund:workflow", {
      detail: { event, projectId: opts?.projectId ?? null, meta },
    }),
  );

  void api
    .post("/api/workflow-events", {
      event,
      project_id: opts?.projectId ?? null,
      meta,
    })
    .catch(() => {
      /* instrumentation must never break the product path */
    });
}
