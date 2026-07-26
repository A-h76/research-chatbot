import { useEffect } from "react";

/** Scroll/focus an element marked with data-workspace-ref matching the URL ref. */
export function useWorkspaceFocus(focusRef?: string | null) {
  useEffect(() => {
    if (!focusRef) return;
    const id = window.setTimeout(() => {
      const el = document.querySelector(
        `[data-workspace-ref="${CSS.escape(focusRef)}"]`,
      ) as HTMLElement | null;
      if (!el) return;
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.focus({ preventScroll: true });
    }, 80);
    return () => window.clearTimeout(id);
  }, [focusRef]);
}
