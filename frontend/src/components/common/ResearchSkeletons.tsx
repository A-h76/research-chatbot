/**
 * Structured research skeletons — layout that mirrors the real UI
 * (Animaster-style bars, not blank white panels). Motion is subtle only.
 */
import { motion, useReducedMotion } from "framer-motion";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function Stagger({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

/** Dense library paper rows — title · meta · badge. */
export function LibraryPapersSkeleton({
  rows = 7,
  className,
}: {
  rows?: number;
  className?: string;
}) {
  const widths = ["w-[72%]", "w-[58%]", "w-[81%]", "w-[64%]", "w-[70%]", "w-[55%]", "w-[76%]"];
  const metas = ["w-40", "w-32", "w-48", "w-36", "w-44", "w-28", "w-52"];

  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Loading papers"
      className={cn(
        "overflow-hidden rounded-lg border border-border bg-card divide-y divide-border",
        className,
      )}
    >
      {Array.from({ length: rows }).map((_, i) => (
        <Stagger key={i} delay={i * 0.04} className="flex items-center gap-3 px-3 py-3">
          <Skeleton className="size-8 shrink-0 rounded-md" />
          <div className="min-w-0 flex-1 space-y-2">
            <Skeleton className={cn("h-3.5", widths[i % widths.length])} />
            <Skeleton className={cn("h-2.5", metas[i % metas.length])} />
          </div>
          <Skeleton className="h-5 w-16 shrink-0 rounded-full" />
          <Skeleton className="hidden h-5 w-14 shrink-0 rounded-md sm:block" />
        </Stagger>
      ))}
    </div>
  );
}

/** Library readiness strip while health loads. */
export function LibraryHealthSkeleton({ className }: { className?: string }) {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Loading library health"
      className={cn("border-b border-border/70 pb-5", className)}
    >
      <Skeleton className="h-3.5 w-36" />
      <Skeleton className="mt-2 h-3 w-56" />
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-6 w-10" />
            <Skeleton className="h-2.5 w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** Writing desk — manuscript-first skeleton (docks closed by default). */
export function WritingDeskSkeleton({ className }: { className?: string }) {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Loading writing desk"
      className={cn("flex min-h-0 flex-1 flex-col gap-2", className)}
    >
      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-border pb-2">
        <Skeleton className="h-8 w-28 rounded-md" />
        <Skeleton className="h-8 w-40 rounded-md" />
        <Skeleton className="h-8 w-16 rounded-md" />
        <Skeleton className="h-8 w-36 rounded-md" />
        <Skeleton className="h-8 w-16 rounded-md" />
        <Skeleton className="ml-auto h-4 w-14" />
      </div>

      <Stagger delay={0.05} className="flex min-h-0 flex-1 flex-col gap-2">
        <Skeleton className="h-8 w-full max-w-md rounded-md" />
        <div className="manuscript-surface flex min-h-0 flex-1 flex-col gap-3 rounded-lg border border-border/80 bg-[#faf9f7] p-5 dark:bg-[#121212]">
          <Skeleton className="mx-auto h-3.5 w-[90%] max-w-[42rem] bg-muted/80" />
          <Skeleton className="mx-auto h-3.5 w-[84%] max-w-[42rem] bg-muted/80" />
          <Skeleton className="mx-auto h-3.5 w-[88%] max-w-[42rem] bg-muted/80" />
          <Skeleton className="mx-auto h-3.5 w-[62%] max-w-[42rem] bg-muted/80" />
          <Skeleton className="mx-auto mt-4 h-3.5 w-[90%] max-w-[42rem] bg-muted/80" />
          <Skeleton className="mx-auto h-3.5 w-[78%] max-w-[42rem] bg-muted/80" />
          <Skeleton className="mx-auto h-3.5 w-[85%] max-w-[42rem] bg-muted/80" />
          <Skeleton className="mx-auto h-3.5 w-[40%] max-w-[42rem] bg-muted/80" />
        </div>
      </Stagger>
    </div>
  );
}

/** Home continue-research skeleton (replaces flat blocks). */
export function HomeResearchSkeleton({ className }: { className?: string }) {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Loading research home"
      className={cn("space-y-8 py-6", className)}
    >
      <Stagger className="space-y-2">
        <Skeleton className="h-7 w-56 max-w-full" />
        <Skeleton className="h-3.5 w-72 max-w-full" />
      </Stagger>

      <Stagger delay={0.05} className="grid gap-3 lg:grid-cols-[1.35fr_1fr]">
        <Skeleton className="h-52 w-full rounded-xl" />
        <div className="space-y-2">
          <Skeleton className="h-[4.5rem] w-full rounded-xl" />
          <Skeleton className="h-[4.5rem] w-full rounded-xl" />
          <Skeleton className="h-[4.5rem] w-full rounded-xl" />
        </div>
      </Stagger>

      <Stagger delay={0.1} className="space-y-3">
        <Skeleton className="h-4 w-36" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </Stagger>
    </div>
  );
}
