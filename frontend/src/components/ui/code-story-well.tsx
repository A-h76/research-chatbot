import { cn } from "@/lib/utils";

/**
 * Replicate-style dark code-story well — Dhund signal teal accent, never orange.
 * Use for API / AI explainers only (Design Language §3.3 / surface map).
 */
export function CodeStoryWell({
  eyebrow = "Example",
  children,
  className,
  mono = true,
}: {
  eyebrow?: string;
  children: React.ReactNode;
  className?: string;
  /** Prefer mono for code; set false for short narrative pull-quotes */
  mono?: boolean;
}) {
  return (
    <figure
      className={cn(
        "overflow-hidden rounded-md border border-white/10 bg-signal-900 text-[#e8f4f3]",
        className,
      )}
      data-code-story-well=""
    >
      <figcaption className="flex items-center justify-between border-b border-white/10 px-3 py-1.5">
        <span className="font-mono text-[10px] font-medium uppercase tracking-[0.1em] text-[#5ee0d4]/60]">
          {eyebrow}
        </span>
        <span className="size-1.5 rounded-full bg-[#5ee0d4]/80" aria-hidden />
      </figcaption>
      <div
        className={cn(
          "max-h-48 overflow-auto px-3 py-3 text-[12px] leading-relaxed",
          mono && "font-mono whitespace-pre-wrap break-words text-[#c5ddd9]",
        )}
      >
        {children}
      </div>
    </figure>
  );
}
