/** Research Reviewer durable run types (A-401 reconstruct APIs). */

import type { WritingReview } from "@/features/evidence/hooks/useGroundedWriting";

export type ReviewerFindingDTO = {
  id: number;
  run_id: number;
  code: string;
  severity: string;
  message: string;
  section_id: string | null;
  block_id?: string;
  evidence_ids?: number[];
  status?: string;
  recommendation?: string;
  created_at?: string | null;
};

export type ReviewerRunDTO = {
  id: number;
  document_id: number;
  project_id: number;
  document_version_no: number;
  writing_version: string;
  reviewer_version: string;
  binder_version?: string;
  status: string;
  pass_rate: number;
  sections_checked: number;
  sections_passed: number;
  issue_count: number;
  metrics?: Record<string, unknown>;
  findings?: ReviewerFindingDTO[];
  review?: WritingReview;
  created_at?: string | null;
  finished_at?: string | null;
};

export type ReviewerRunListResponse = {
  document_id: number;
  items: ReviewerRunDTO[];
  count: number;
};
