/**
 * Featured Library spotlight — Continue reading or Recommended.
 */
import { ArrowRight } from "lucide-react";
import type { LibrarySpotlight } from "../libraryListViewModel";
import { paperContextLine, paperTitle } from "../libraryListViewModel";

export function ContinueReadingCard({
  spotlight,
  onContinue,
}: {
  spotlight: LibrarySpotlight;
  onContinue: () => void;
}) {
  const { paper, mode, reason, ctaLabel } = spotlight;
  const meta = paperContextLine(paper);
  const eyebrow =
    mode === "continue" ? "Continue reading" : "Recommended reading";

  return (
    <button
      type="button"
      onClick={onContinue}
      className="group flex w-full items-start gap-3 rounded-xl border border-primary/15 bg-primary/[0.03] px-3.5 py-3.5 text-left transition-[border-color,background-color] duration-200 hover:border-primary/25 hover:bg-primary/[0.045] dark:bg-primary/[0.06]"
    >
      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-text-tertiary">
          {eyebrow}
        </p>
        <p className="line-clamp-2 text-[14px] font-semibold leading-snug tracking-tight text-text-primary">
          {paperTitle(paper)}
        </p>
        {meta ? (
          <p className="truncate text-[12px] text-text-secondary">{meta}</p>
        ) : null}
        <p className="pt-0.5 text-[12px] text-text-tertiary">{reason}</p>
      </div>
      <span className="mt-0.5 inline-flex shrink-0 items-center gap-1 text-[12px] font-medium text-text-accent transition-transform duration-200 group-hover:translate-x-0.5">
        {ctaLabel}
        <ArrowRight className="size-3.5 transition-transform duration-200 group-hover:translate-x-1" />
      </span>
    </button>
  );
}
