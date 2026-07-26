import { cn } from "@/lib/utils";
import {
  aiStateTokenClass,
  resolveAiState,
  type AiStateId,
  type AiStateResolved,
  type ResolveAiStateInput,
} from "../aiState";
import type { PipelineDerived } from "../types";

export type AiStateBadgeProps = {
  state?: AiStateResolved;
  /** Resolve from pipeline + meta when `state` is omitted. */
  derived?: PipelineDerived | null;
  metaStatus?: string | null;
  uploading?: boolean;
  uploadFailed?: boolean;
  className?: string;
  /** Compact = smaller type (Library cards). */
  size?: "sm" | "md";
};

/**
 * Shared AI State Language badge — dot + locked label (never colour alone).
 */
export function AiStateBadge({
  state,
  derived,
  metaStatus,
  uploading,
  uploadFailed,
  className,
  size = "sm",
}: AiStateBadgeProps) {
  const resolved =
    state ??
    resolveAiState({
      derived,
      metaStatus,
      uploading,
      uploadFailed,
    } satisfies ResolveAiStateInput);

  const tokens = aiStateTokenClass(resolved.id);
  const aria = `Status: ${resolved.label}`;

  return (
    <span
      role="status"
      aria-label={aria}
      title={aria}
      className={cn(
        "inline-flex items-center gap-1.5 font-medium",
        size === "sm" ? "text-xs" : "text-sm",
        tokens.text,
        className,
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "inline-block size-2 shrink-0 rounded-full",
          tokens.dot,
          tokens.pulse && "ai-state-pulse",
        )}
      />
      <span>{resolved.label}</span>
    </span>
  );
}

/** Tiny helper for upload-queue rows that only know a coarse M2 status. */
export function aiStateFromUploadStatus(
  status: "uploading" | "uploaded" | "failed",
): AiStateResolved {
  if (status === "uploading") return resolveAiState({ uploading: true });
  if (status === "failed") return resolveAiState({ uploadFailed: true });
  return resolveAiState({ metaStatus: "pending" }); // Uploaded → Queued until pipeline advances
}

export type { AiStateId, AiStateResolved };
