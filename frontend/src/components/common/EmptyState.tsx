import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Calm empty surface — title + why + optional next action.
 * Sprint 4: soft entrance, honest pending pulse (never fake progress %).
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  pending,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  /** Show indeterminate progress while a background process is honestly running. */
  pending?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "dhund-enter flex flex-col items-center justify-center gap-2 py-14 text-center sm:py-16",
        className,
      )}
    >
      {icon && <div className="mb-1 text-muted-foreground">{icon}</div>}
      <p className="text-sm font-medium text-foreground">{title}</p>
      {description && (
        <p className="max-w-md text-sm leading-relaxed text-muted-foreground">{description}</p>
      )}
      {pending && (
        <div
          className="mt-3 h-1 w-40 overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-label="Still working"
          aria-valuetext="In progress"
        >
          <div className="dhund-progress-indeterminate h-full w-1/2 rounded-full bg-primary/70" />
        </div>
      )}
      {action && <div className="mt-4 flex flex-wrap items-center justify-center gap-2">{action}</div>}
    </div>
  );
}
