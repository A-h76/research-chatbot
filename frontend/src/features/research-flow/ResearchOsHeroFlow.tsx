import { useRef } from "react";
import { BeamCanvas, FlowNode } from "./FlowPrimitives";

/**
 * Landing / marketing Research OS hero diagram.
 * Sources converge into Dhund Core, then flow toward publication.
 */
export function ResearchOsHeroFlow({ className }: { className?: string }) {
  const pubmedRef = useRef<HTMLDivElement>(null);
  const arxivRef = useRef<HTMLDivElement>(null);
  const orcidRef = useRef<HTMLDivElement>(null);
  const driveRef = useRef<HTMLDivElement>(null);
  const uploadRef = useRef<HTMLDivElement>(null);
  const coreRef = useRef<HTMLDivElement>(null);
  const analysisRef = useRef<HTMLDivElement>(null);
  const evidenceRef = useRef<HTMLDivElement>(null);
  const writingRef = useRef<HTMLDivElement>(null);
  const reviewerRef = useRef<HTMLDivElement>(null);
  const publishRef = useRef<HTMLDivElement>(null);

  const sources = [
    { ref: pubmedRef, label: "PubMed" },
    { ref: arxivRef, label: "arXiv" },
    { ref: orcidRef, label: "ORCID" },
    { ref: driveRef, label: "Drive" },
    { ref: uploadRef, label: "Upload" },
  ] as const;

  const pipeline = [
    { ref: analysisRef, label: "Analysis" },
    { ref: evidenceRef, label: "Evidence" },
    { ref: writingRef, label: "Writing" },
    { ref: reviewerRef, label: "Reviewer" },
    { ref: publishRef, label: "Publish" },
  ] as const;

  const beams = [
    ...sources.map((s, i) => ({
      from: s.ref,
      to: coreRef,
      delay: 0.15 * i,
      curvature: 36,
    })),
    { from: coreRef, to: analysisRef, delay: 1.0, curvature: 6 },
    { from: analysisRef, to: evidenceRef, delay: 1.25, curvature: 6 },
    { from: evidenceRef, to: writingRef, delay: 1.5, curvature: 6 },
    { from: writingRef, to: reviewerRef, delay: 1.75, curvature: 6 },
    { from: reviewerRef, to: publishRef, delay: 2.0, curvature: 6 },
  ];

  return (
    <BeamCanvas className={className} beams={beams}>
      <div className="flex flex-col items-center gap-8 px-2 py-4">
        <div className="flex flex-wrap items-center justify-center gap-3">
          {sources.map((s) => (
            <FlowNode key={s.label} ref={s.ref} label={s.label} sub="source" />
          ))}
        </div>
        <FlowNode
          ref={coreRef}
          label="Dhund Core"
          sub="Research OS"
          active
          className="min-w-[7.5rem] border-primary/40 px-4 py-3"
        />
        <div className="flex flex-wrap items-center justify-center gap-3">
          {pipeline.map((s) => (
            <FlowNode key={s.label} ref={s.ref} label={s.label} />
          ))}
        </div>
        <p className="max-w-sm text-center text-[11px] text-muted-foreground">
          Everything converges here — then flows through one research pipeline.
        </p>
      </div>
    </BeamCanvas>
  );
}
