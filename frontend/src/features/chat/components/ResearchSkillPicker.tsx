import { Layers } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import type { ResearchSkillId } from "../types";
import { RESEARCH_SKILLS } from "../types";

export function ResearchSkillPicker({
  value,
  onChange,
}: {
  value: ResearchSkillId;
  onChange: (skill: ResearchSkillId) => void;
}) {
  const current = RESEARCH_SKILLS.find((s) => s.id === value) ?? RESEARCH_SKILLS[0];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs transition-colors hover:bg-hover hover:text-foreground",
          value === "ask"
            ? "text-muted-foreground"
            : "border-primary/40 bg-accent-soft text-primary",
        )}
        title="Research skill"
      >
        <Layers className="size-3.5" />
        <span>{current.label}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        {RESEARCH_SKILLS.map((s) => (
          <DropdownMenuItem
            key={s.id}
            onClick={() => onChange(s.id)}
            className="flex flex-col items-start gap-0.5"
          >
            <span className="text-sm font-medium">{s.label}</span>
            <span className="text-[11px] text-muted-foreground">{s.description}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
