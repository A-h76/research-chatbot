import type { ProjectResearchPreset } from "@/types/api";

/** Build project Research tab URL with optional preset or freeform query. */
export function projectResearchUrl(
  projectId: number,
  opts?: { preset?: ProjectResearchPreset; query?: string },
): string {
  const params = new URLSearchParams({ tab: "research" });
  if (opts?.preset) params.set("preset", opts.preset);
  if (opts?.query?.trim()) params.set("query", opts.query.trim());
  return `/projects/${projectId}?${params.toString()}`;
}
