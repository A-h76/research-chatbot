import { Star } from "lucide-react";
import { IMPORTANCE_RANGE } from "@/lib/constants";
import { cn } from "@/lib/utils";

export function ImportanceStars({
  value,
  onChange,
  readOnly,
}: {
  value: number;
  onChange?: (v: number) => void;
  readOnly?: boolean;
}) {
  return (
    <div className="flex items-center gap-0.5">
      {IMPORTANCE_RANGE.map((n) => (
        <button
          key={n}
          type="button"
          disabled={readOnly}
          onClick={() => onChange?.(n)}
          className={cn("p-0.5", !readOnly && "hover:scale-110")}
          title={`Importance ${n}`}
          aria-label={`Set importance ${n}`}
        >
          <Star
            className={cn(
              "size-3.5",
              n <= value ? "fill-primary text-primary" : "text-muted-foreground/40"
            )}
          />
        </button>
      ))}
    </div>
  );
}
