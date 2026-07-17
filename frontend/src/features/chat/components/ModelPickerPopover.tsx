import { useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { useModels } from "@/features/models/useModels";
import { cn } from "@/lib/utils";

export function ModelPickerPopover({
  value,
  onChange,
  compact,
}: {
  value: string;
  onChange: (model: string) => void;
  compact?: boolean;
}) {
  const { data } = useModels();
  const models = data?.models ?? [];
  const [open, setOpen] = useState(false);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-hover hover:text-foreground",
          compact && "border-none px-2 hover:bg-muted"
        )}
      >
        <span className="max-w-[140px] truncate">{value || "Select model"}</span>
        <ChevronDown className="size-3" />
      </PopoverTrigger>
      <PopoverContent align="start" className="w-72 p-0">
        <Command>
          <CommandInput placeholder="Search models…" />
          <CommandList>
            <CommandEmpty>No models found.</CommandEmpty>
            {models.map((m) => (
              <CommandItem
                key={m}
                value={m}
                onSelect={() => {
                  onChange(m);
                  setOpen(false);
                }}
              >
                <span className="flex-1 truncate">{m}</span>
                {m === value && <Check className="size-4 text-primary" />}
              </CommandItem>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
