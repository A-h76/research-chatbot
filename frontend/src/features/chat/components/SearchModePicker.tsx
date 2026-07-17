import { Globe } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SEARCH_MODES } from "@/lib/constants";
import type { SearchMode } from "@/types/api";
import { cn } from "@/lib/utils";

const LABEL: Record<SearchMode, string> = { off: "Off", auto: "Auto", on: "Always" };

export function SearchModePicker({
  value,
  onChange,
}: {
  value: SearchMode;
  onChange: (mode: SearchMode) => void;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs transition-colors hover:bg-hover hover:text-foreground",
          value === "off" ? "text-muted-foreground" : "border-primary/40 bg-accent-soft text-primary"
        )}
        title="Web search mode"
      >
        <Globe className="size-3.5" />
        <span className="hidden sm:inline">{LABEL[value]}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {SEARCH_MODES.map((m) => (
          <DropdownMenuItem key={m.value} onClick={() => onChange(m.value)}>
            {m.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
