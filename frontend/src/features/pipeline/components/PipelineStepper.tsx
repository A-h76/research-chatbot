import { AlertCircle, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  resolveAiStepper,
  type AiStepperNode,
  type AiStateId,
} from "../aiState";
import type { PipelineDerived } from "../types";

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
      className={cn("w-full overflow-x-auto", className)}
    >
      <ol className="flex min-w-max items-start gap-0">
        {nodes.map((node, i) => (
          <li key={node.id} className="flex items-start">
            <StepperNode node={node} />
            {i < nodes.length - 1 && (
              <span
                aria-hidden="true"
                className={cn(
                  "mt-2 h-px w-4 shrink-0 sm:w-6",
                  node.state === "complete" ? "bg-sem-ready" : "bg-ink-200",
                )}
              />
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function activeFill(id: Exclude<AiStateId, "needs_attention">): string {
  if (id === "uploading") return "bg-sem-info";
  if (id === "queued") return "bg-sem-queued";
  if (id === "understanding" || id === "classifying") return "bg-sem-running";
  if (id === "chat_ready") return "bg-signal-600";
  return "bg-sem-ready";
}

function StepperNode({ node }: { node: AiStepperNode }) {
  const pulse =
    node.state === "active" &&
    (node.id === "uploading" || node.id === "understanding" || node.id === "classifying");

  return (
    <div className="flex w-[4.5rem] flex-col items-center gap-1.5 sm:w-[5.25rem]">
      <span
        aria-hidden="true"
        className={cn(
          "flex size-4 items-center justify-center rounded-full",
          node.state === "pending" && "border-2 border-ink-300 bg-transparent",
          node.state === "active" && activeFill(node.id),
          node.state === "active" && pulse && "ai-state-pulse",
          node.state === "complete" &&
            (node.id === "chat_ready" ? "bg-signal-600" : "bg-sem-ready"),
          node.state === "error" && "bg-sem-error",
        )}
      >
        {node.state === "complete" && (
          <Check className="size-2.5 text-white" strokeWidth={3} />
        )}
        {node.state === "error" && (
          <AlertCircle className="size-2.5 text-white" strokeWidth={2.5} />
        )}
        {node.state === "active" && (
          <span className="size-1.5 rounded-full bg-white/90" />
        )}
      </span>
      <span
        className={cn(
          "text-center text-[10px] leading-tight sm:text-[11px]",
          node.state === "pending" && "text-ink-500",
          node.state === "active" && "font-medium text-ink-900",
          node.state === "complete" && "text-ink-900",
          node.state === "error" && "font-medium text-sem-error",
        )}
      >
        {node.label}
      </span>
      <span className="sr-only">
        {node.label}: {node.state}
      </span>
    </div>
  );
}
