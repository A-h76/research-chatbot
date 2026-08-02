import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function HomeSectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-foreground/55">
      {children}
    </p>
  );
}

export function HomeRecentList({
  items,
  empty,
}: {
  items: {
    key: string;
    label: string;
    meta?: string;
    icon: LucideIcon;
    onClick: () => void;
  }[];
  empty: string;
}) {
  if (items.length === 0) {
    if (!empty) return null;
    return (
      <p className="rounded-xl border border-border bg-card px-3.5 py-4 text-[13px] text-foreground/65">
        {empty}
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card divide-y divide-border">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <button
            key={item.key}
            type="button"
            onClick={item.onClick}
            className={cn(
              "flex w-full items-center gap-3 px-3.5 py-2.5 text-left",
              "transition-colors duration-150 hover:bg-muted/50",
            )}
          >
            <Icon className="size-3.5 shrink-0 text-foreground/45" aria-hidden />
            <span className="min-w-0 flex-1 truncate text-[13px] text-foreground">
              {item.label}
            </span>
            {item.meta ? (
              <span className="shrink-0 text-[11px] text-foreground/55">{item.meta}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
