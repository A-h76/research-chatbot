import { Thermometer } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const DEFAULT_TEMP = 1.0;

export function TemperatureControl({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (v: number | null) => void;
}) {
  const effective = value ?? DEFAULT_TEMP;
  return (
    <Popover>
      <PopoverTrigger
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-hover hover:text-foreground",
          value !== null && "border-primary/40 text-primary"
        )}
        title="Temperature"
      >
        <Thermometer className="size-3.5" />
        <span className="hidden sm:inline">{effective.toFixed(1)}</span>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-64 gap-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium">Temperature</span>
          <span className="text-xs text-muted-foreground">{effective.toFixed(2)}</span>
        </div>
        <Slider
          min={0}
          max={2}
          step={0.05}
          value={[effective]}
          onValueChange={(v) => onChange(Array.isArray(v) ? v[0] : v)}
        />
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span>Precise</span>
          <span>Creative</span>
        </div>
        <Button variant="ghost" size="sm" className="self-end" onClick={() => onChange(null)}>
          Reset to default
        </Button>
      </PopoverContent>
    </Popover>
  );
}
