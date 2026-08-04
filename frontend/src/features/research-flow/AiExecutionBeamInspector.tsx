import { useRef } from "react";
import { BeamCanvas, FlowNode } from "./FlowPrimitives";
import { cn } from "@/lib/utils";

export type AiExecutionSummary = {
  research_job?: string | null;
  capability?: string | null;
  execution_policy?: string | null;
  provider?: string | null;
  model?: string | null;
  prompt_version?: string | null;
  router_version?: string | null;
  execution_id?: string | null;
};

/**
 * AI Execution / Capability Router inspector — visualizes how Dhund produced an answer.
 */
export function AiExecutionBeamInspector({
  execution,
  className,
  compact,
}: {
  execution?: AiExecutionSummary | null;
  className?: string;
  compact?: boolean;
}) {
  const jobRef = useRef<HTMLDivElement>(null);
  const routerRef = useRef<HTMLDivElement>(null);
  const promptRef = useRef<HTMLDivElement>(null);
  const modelRef = useRef<HTMLDivElement>(null);
  const validRef = useRef<HTMLDivElement>(null);
  const ledgerRef = useRef<HTMLDivElement>(null);

  const job = execution?.research_job || "research_job";
  const model = execution?.model || "model";
  const provider = execution?.provider || "provider";
  const prompt = execution?.prompt_version || "prompt";

  const beams = [
    { from: jobRef, to: routerRef, delay: 0 },
    { from: routerRef, to: promptRef, delay: 0.25 },
    { from: promptRef, to: modelRef, delay: 0.5 },
    { from: modelRef, to: validRef, delay: 0.75 },
    { from: validRef, to: ledgerRef, delay: 1.0 },
  ];

  return (
    <section
      className={cn(
        "rounded-xl border border-border bg-card/50 p-3",
        compact && "p-2.5",
        className,
      )}
      aria-label="AI execution path"
    >
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <h3 className="text-xs font-semibold tracking-tight text-foreground">AI execution</h3>
        {execution?.router_version ? (
          <span className="text-[10px] text-muted-foreground">router v{execution.router_version}</span>
        ) : null}
      </div>
      <p className="mb-3 text-[11px] text-muted-foreground">
        How Dhund resolved this response — Capability Router → ledger.
      </p>
      <BeamCanvas beams={beams}>
        <div className="flex flex-wrap items-center justify-center gap-2.5 px-1 py-2">
          <FlowNode ref={jobRef} label="Research Job" sub={job.replaceAll("_", " ")} active />
          <FlowNode ref={routerRef} label="Capability Router" sub={execution?.capability || "route"} />
          <FlowNode ref={promptRef} label="Prompt" sub={prompt} />
          <FlowNode ref={modelRef} label={model} sub={provider} />
          <FlowNode ref={validRef} label="Validation" sub="evidence / schema" />
          <FlowNode ref={ledgerRef} label="AI Ledger" sub={execution?.execution_id ? "recorded" : "record"} />
        </div>
      </BeamCanvas>
      {execution?.execution_policy ? (
        <p className="mt-2 text-[10px] text-muted-foreground">
          Policy: {execution.execution_policy.replaceAll("_", " ")}
        </p>
      ) : null}
    </section>
  );
}
