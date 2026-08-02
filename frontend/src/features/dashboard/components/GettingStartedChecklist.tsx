import { useNavigate } from "react-router-dom";
import { Check, Circle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChecklistItem } from "../homeMaturity";

export function GettingStartedChecklist({ items }: { items: ChecklistItem[] }) {
  const navigate = useNavigate();
  const done = items.filter((i) => i.done).length;
  const total = items.length;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <section>
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight text-foreground">
            Getting started
          </h2>
          <p className="mt-0.5 text-[13px] text-foreground/65">
            {done} / {total} Complete
          </p>
        </div>
        <span className="text-[12px] tabular-nums text-foreground/55">{pct}%</span>
      </div>

      <div className="mb-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all duration-300 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>

      <ul className="overflow-hidden rounded-xl border border-border bg-card divide-y divide-border">
        {items.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => {
                if (item.href) navigate(item.href);
              }}
              className={cn(
                "flex w-full items-center gap-3 px-3.5 py-3 text-left transition-colors duration-150",
                "hover:bg-muted/50",
                item.done && "opacity-70",
              )}
            >
              {item.done ? (
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <Check className="size-3" strokeWidth={2.5} aria-hidden />
                </span>
              ) : (
                <Circle className="size-5 shrink-0 text-foreground/35" aria-hidden />
              )}
              <span
                className={cn(
                  "text-[13px]",
                  item.done ? "text-foreground/60 line-through" : "text-foreground",
                )}
              >
                {item.label}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
