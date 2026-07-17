// Mirrors the backend guards in server.py (REASONING_EFFORT_PREFIXES /
// NO_TEMPERATURE_PREFIXES) so the UI hides controls the API would ignore.
const REASONING_EFFORT_PREFIXES = ["o1", "o3", "o4", "gpt-5"];
const NO_TEMPERATURE_PREFIXES = ["o1", "o3", "o4"];

export function supportsReasoningEffort(model: string): boolean {
  return REASONING_EFFORT_PREFIXES.some((p) => model.startsWith(p));
}

export function supportsTemperature(model: string): boolean {
  return !NO_TEMPERATURE_PREFIXES.some((p) => model.startsWith(p));
}
