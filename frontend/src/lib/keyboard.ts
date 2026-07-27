/** True when keyboard shortcuts should not fire (user is typing). */
export function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  const ce = target.getAttribute("contenteditable");
  if (ce === "" || ce === "true") return true;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (target.closest("[role='textbox'], [contenteditable='true'], [contenteditable='']")) {
    return true;
  }
  return false;
}
