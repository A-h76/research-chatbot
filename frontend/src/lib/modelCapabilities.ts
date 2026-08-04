// Mirrors the backend guards in server.py (REASONING_EFFORT_PREFIXES /
// NO_TEMPERATURE_PREFIXES / NO_STREAMING_PREFIXES) so the UI hides controls
// the API would reject.
// gpt-5 / gpt-5.5 / gpt-5-mini reject `temperature` (400); use reasoning effort.
// gpt-5.5-pro rejects streaming and reasoning.effort=low.
const REASONING_EFFORT_PREFIXES = ["o1", "o3", "o4", "gpt-5"];
const NO_TEMPERATURE_PREFIXES = ["o1", "o3", "o4", "gpt-5"];
const PRO_NO_LOW_EFFORT_PREFIXES = ["gpt-5.5-pro", "gpt-5.4-pro", "gpt-5.2-pro"];

export function supportsReasoningEffort(model: string): boolean {
  return REASONING_EFFORT_PREFIXES.some((p) => model.startsWith(p));
}

export function supportsTemperature(model: string): boolean {
  return !NO_TEMPERATURE_PREFIXES.some((p) => model.startsWith(p));
}

/** Pro SKUs reject ``low``; only medium / high / xhigh. */
export function isProReasoningModel(model: string): boolean {
  return PRO_NO_LOW_EFFORT_PREFIXES.some((p) => model.startsWith(p));
}

export function allowedReasoningEfforts(model: string): Array<"low" | "medium" | "high"> {
  if (isProReasoningModel(model)) return ["medium", "high"];
  return ["low", "medium", "high"];
}

/** Clamp a stored effort so Pro models never keep ``low``. */
export function normalizeReasoningEffort(
  model: string,
  effort: "low" | "medium" | "high" | null
): "low" | "medium" | "high" | null {
  if (effort == null) return null;
  if (isProReasoningModel(model) && effort === "low") return "medium";
  return effort;
}
