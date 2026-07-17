import { Brain } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { REASONING_EFFORTS } from "@/lib/constants";
import { cn } from "@/lib/utils";

type Effort = "low" | "medium" | "high" | null;

export function ReasoningEffortControl({
  value,
  onChange,
}: {
  value: Effort;
  onChange: (v: Effort) => void;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs capitalize text-muted-foreground transition-colors hover:bg-hover hover:text-foreground",
          value && "border-primary/40 text-primary"
        )}
        title="Reasoning effort"
      >
        <Brain className="size-3.5" />
        <span className="hidden sm:inline">{value ?? "Reasoning"}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        <DropdownMenuCheckboxItem checked={value === null} onClick={() => onChange(null)}>
          Default
        </DropdownMenuCheckboxItem>
        {REASONING_EFFORTS.map((e) => (
          <DropdownMenuCheckboxItem key={e} checked={value === e} onClick={() => onChange(e)} className="capitalize">
            {e}
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
