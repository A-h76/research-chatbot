import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Workspace object header — title + meta + status.
 * No marketing cards; identity only (DESIGN-SYSTEM-v2 §9.2).
 */
export function ObjectHeader({
  title,
  meta,
  status,
  actions,
  className,
}: {
  title: ReactNode;
  meta?: ReactNode;
  status?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("space-y-2", className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-1">
          <h1 className="text-display font-semibold leading-snug tracking-tight text-foreground">
            {title}
          </h1>
          {meta ? (
            <div className="text-meta text-muted-foreground">{meta}</div>
          ) : null}
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
      </div>
      {status ? (
        <div className="flex flex-wrap items-center gap-2">{status}</div>
      ) : null}
    </header>
  );
}
