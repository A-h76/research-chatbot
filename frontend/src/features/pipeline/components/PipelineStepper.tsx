import { AlertCircle, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  resolveAiStepper,
  type AiStepperNode,
  type AiStateId,
} from "../aiState";
import type { PipelineDerived } from "../types";

/**
 * Pipeline stage chips — Cursor timeline *pattern*, Dhund `sem.*` tokens only.
 * Color stays inside this strip (Design Language §2 / Cursor mapping).
 */
export function PipelineStepper({
  derived,
  metaStatus,
  uploading,
  className,
}: {
  derived?: PipelineDerived | null;
  metaStatus?: string | null;
  uploading?: boolean;
  className?: string;
}) {
  const nodes = resolveAiStepper(derived, { metaStatus, uploading });

  return (
    <nav
      aria-label="Pipeline status"
      className={cn(
        "w-full overflow-x-auto rounded-md bg-muted/30 px-1.5 py-1.5",
        className,
      )}
      data-pipeline-stage-strip=""
    >
      <ol className="flex min-w-max items-center gap-1.5">
        {nodes.map((node, i) => (
          <li key={node.id} className="flex items-center gap-1.5">
            <StageChip node={node} />
            {i < nodes.length - 1 && (
              <span
                aria-hidden="true"
                className={cn(
                  "h-px w-2.5 shrink-0 sm:w-3.5",
                  node.state === "complete" ? "bg-sem-ready/60" : "bg-ink-200",
                )}
              />
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function chipTone(node: AiStepperNode): string {
  if (node.state === "pending") {
    return "border-border bg-transparent text-ink-500";
  }
  if (node.state === "error") {
    return "border-sem-error/40 bg-sem-error/10 text-sem-error";
  }
  if (node.state === "complete") {
    if (node.id === "chat_ready") {
      return "border-signal-600/35 bg-signal-600/10 text-signal-600";
    }
    return "border-sem-ready/35 bg-sem-ready/10 text-sem-ready";
  }
  // active
  return activeChipTone(node.id);
}

function activeChipTone(id: Exclude<AiStateId, "needs_attention">): string {
  if (id === "uploading") return "border-sem-info/40 bg-sem-info/15 text-sem-info";
  if (id === "queued") return "border-sem-queued/40 bg-sem-queued/15 text-sem-queued";
  if (id === "understanding" || id === "classifying") {
    return "border-sem-running/40 bg-sem-running/15 text-sem-running";
  }
  if (id === "chat_ready") return "border-signal-600/40 bg-signal-600/15 text-signal-600";
  return "border-sem-ready/40 bg-sem-ready/15 text-sem-ready";
}

function StageChip({ node }: { node: AiStepperNode }) {
  const pulse =
    node.state === "active" &&
    (node.id === "uploading" || node.id === "understanding" || node.id === "classifying");

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded border px-2 py-1 text-[10px] font-medium leading-none sm:text-[11px]",
        chipTone(node),
        pulse && "ai-state-pulse",
      )}
    >
      <span aria-hidden="true" className="flex size-3.5 items-center justify-center">
        {node.state === "complete" && <Check className="size-2.5" strokeWidth={3} />}
        {node.state === "error" && <AlertCircle className="size-2.5" strokeWidth={2.5} />}
        {node.state === "active" && (
          <span className="size-1.5 rounded-full bg-current opacity-90" />
        )}
        {node.state === "pending" && (
          <span className="size-1.5 rounded-full border border-current opacity-40" />
        )}
      </span>
      <span>{node.label}</span>
      <span className="sr-only">
        {node.label}: {node.state}
      </span>
    </span>
  );
}
