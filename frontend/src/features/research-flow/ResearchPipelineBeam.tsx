import { useRef } from "react";
import { BeamCanvas, FlowNode } from "./FlowPrimitives";
import { cn } from "@/lib/utils";

export const RESEARCH_PIPELINE_STEPS = [
  "Question",
  "Discover",
  "Library",
  "Analysis",
  "Evidence",
  "Writing",
  "Reviewer",
  "Publish",
] as const;

export type ResearchPipelineStep = (typeof RESEARCH_PIPELINE_STEPS)[number];

/**
 * In-app research pipeline progress — knowledge flowing question → publish.
 * `activeIndex` highlights the current stage (0-based); prior stages are done.
 */
export function ResearchPipelineBeam({
  activeIndex = 0,
  className,
  title = "Research pipeline",
}: {
  activeIndex?: number;
  className?: string;
  title?: string;
}) {
  const qRef = useRef<HTMLDivElement>(null);
  const dRef = useRef<HTMLDivElement>(null);
  const lRef = useRef<HTMLDivElement>(null);
  const aRef = useRef<HTMLDivElement>(null);
  const eRef = useRef<HTMLDivElement>(null);
  const wRef = useRef<HTMLDivElement>(null);
  const rRef = useRef<HTMLDivElement>(null);
  const pRef = useRef<HTMLDivElement>(null);
  const refs = [qRef, dRef, lRef, aRef, eRef, wRef, rRef, pRef];

  const beams = refs.slice(0, -1).map((from, i) => ({
    from,
    to: refs[i + 1],
    delay: 0.2 * i,
    curvature: 10,
  }));

  return (
    <section className={cn("rounded-xl border border-border bg-card/40 p-4", className)}>
      <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        From research question to publishable output — one continuous flow.
      </p>
      <BeamCanvas className="mt-5 overflow-x-auto" beams={beams}>
        <div className="flex min-w-max items-center justify-start gap-3 px-1 py-3">
          {RESEARCH_PIPELINE_STEPS.map((label, i) => (
            <FlowNode
              key={label}
              ref={refs[i]}
              label={label}
              active={i === activeIndex}
              done={i < activeIndex}
            />
          ))}
        </div>
      </BeamCanvas>
    </section>
  );
}

/** Map project hub stats → approximate pipeline stage index. */
export function pipelineIndexFromProjectStats(stats: {
  papers: number;
  evidence_count?: number;
  notes_count?: number;
  writing_count?: number;
}): number {
  if ((stats.writing_count ?? 0) > 0) return 5; // Writing
  if ((stats.notes_count ?? 0) > 0) return 4; // Evidence/notes stage
  if ((stats.evidence_count ?? 0) > 0) return 4;
  if (stats.papers > 0) return 3; // Analysis
  return 1; // Discover / getting started
}
