import { Check } from "lucide-react";
import { countCitationMarkers, countWords } from "@/features/projects/projectWorkspaceNav";
import type { WritingSaveState } from "../utils/autosavePolicy";
import { cn } from "@/lib/utils";

export function WritingStudioFooter({
  content,
  saveState,
}: {
  content: string;
  saveState: WritingSaveState;
}) {
  const words = countWords(content);
  const cites = countCitationMarkers(content);
  const saved =
    saveState === "idle" || saveState === "saved"
      ? "All changes saved"
      : saveState === "saving" || saveState === "scheduled"
        ? "Saving…"
        : saveState === "dirty"
          ? "Unsaved changes"
          : saveState === "conflict"
            ? "Conflict detected"
            : "Save failed";
  const ok = saveState === "idle" || saveState === "saved";

  return (
    <footer
      className="flex shrink-0 items-center gap-3 border-t border-border bg-muted/30 px-4 py-1.5 text-[12px] text-muted-foreground"
      data-testid="writing-studio-footer"
    >
      <span className="tabular-nums">{words} words</span>
      <span className="text-border">·</span>
      <span className="tabular-nums">{cites} citations</span>
      <span className="ml-auto flex items-center gap-1.5" role="status" aria-live="polite">
        {ok ? <Check className={cn("size-3.5 text-sem-ready")} aria-hidden /> : null}
        <span className={ok ? "text-foreground/80" : undefined}>{saved}</span>
      </span>
    </footer>
  );
}
