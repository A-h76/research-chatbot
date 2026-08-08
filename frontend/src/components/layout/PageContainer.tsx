import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function PageContainer({
  title,
  description,
  actions,
  children,
  maxWidth = "5xl",
  dense,
  fill,
}: {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  /** T4 Compare uses wider stage; Writing uses full bleed. */
  maxWidth?: "5xl" | "6xl" | "full";
  /** Tool pages: tighter vertical rhythm. */
  dense?: boolean;
  /** Fill parent height; children flex into remaining space (no page scroll). */
  fill?: boolean;
}) {
  const showHeader = Boolean(title || description || actions);

  return (
    <div
      className={cn(
        "h-full",
        fill
          ? "flex min-h-0 flex-col overflow-hidden"
          : "scrollbar-thin overflow-y-auto",
      )}
    >
      <div
        className={cn(
          "mx-auto w-full px-5 sm:px-8",
          fill && "flex min-h-0 flex-1 flex-col",
          dense ? (fill ? "py-3" : "py-5") : "py-8",
          maxWidth === "full"
            ? "max-w-none"
            : maxWidth === "6xl"
              ? "max-w-6xl"
              : "max-w-5xl",
        )}
      >
        {showHeader && (
          <div
            className={cn(
              "flex items-start justify-between gap-4",
              fill ? "mb-2 shrink-0" : dense ? "mb-4" : "mb-5",
            )}
          >
            <div>
              {title && (
                <h1 className="text-[20px] font-semibold tracking-tight text-text-primary">
                  {title}
                </h1>
              )}
              {description && (
                <p
                  className={cn(
                    "text-[13px] text-text-secondary",
                    title ? "mt-1" : undefined,
                  )}
                >
                  {description}
                </p>
              )}
            </div>
            {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
          </div>
        )}
        {fill ? (
          <div className="flex min-h-0 flex-1 flex-col">{children}</div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
