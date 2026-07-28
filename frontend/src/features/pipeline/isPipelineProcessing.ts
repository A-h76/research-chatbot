import type { PipelineDerived } from "./types";

export function isPipelineProcessing(
  derived: PipelineDerived,
  metaStatus?: string | null,
): boolean {
  return (
    derived.isQueued ||
    derived.isRunning ||
    derived.isAbsent ||
    metaStatus === "pending" ||
    metaStatus === "running"
  );
}
