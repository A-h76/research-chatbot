import { Brain } from "lucide-react";
import { cn } from "@/lib/utils";

export function MemoryToggle({
  enabled,
  onChange,
}: {
  enabled: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!enabled)}
      title={enabled ? "Memory on — click to disable" : "Memory off — click to enable"}
      aria-pressed={enabled}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors",
        enabled
          ? "border-primary/40 bg-accent-soft text-primary"
          : "border-border text-muted-foreground hover:bg-hover hover:text-foreground"
      )}
    >
      <Brain className="size-3.5" />
      <span className="hidden sm:inline">Memory</span>
    </button>
  );
}
