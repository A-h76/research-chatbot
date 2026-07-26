import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function PageContainer({
  title,
  description,
  actions,
  children,
  maxWidth = "5xl",
  dense,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  /** T4 Compare uses wider stage. */
  maxWidth?: "5xl" | "6xl";
  /** Tool pages: tighter vertical rhythm. */
  dense?: boolean;
}) {
  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div
        className={cn(
          "mx-auto w-full px-5 sm:px-8",
          dense ? "py-5" : "py-8",
          maxWidth === "6xl" ? "max-w-6xl" : "max-w-5xl",
        )}
      >
        <div className={cn("flex items-start justify-between gap-4", dense ? "mb-4" : "mb-5")}>
          <div>
            <h1 className="text-[20px] font-semibold tracking-tight">{title}</h1>
            {description && (
              <p className="mt-1 text-[13px] text-muted-foreground">{description}</p>
            )}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </div>
        {children}
      </div>
    </div>
  );
}
