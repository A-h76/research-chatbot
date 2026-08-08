/**
 * Featured Continue reading card — Library primary continuation.
 */
import { ArrowRight } from "lucide-react";
import type { UserFile } from "@/types/api";
import {
  paperAuthorsShort,
  paperStatusLabel,
  paperTitle,
} from "../libraryListViewModel";

export function ContinueReadingCard({
  paper,
  onContinue,
}: {
  paper: UserFile;
  onContinue: () => void;
}) {
  const authors = paperAuthorsShort(paper);
  const year = paper.year?.trim() || null;
  const meta = [authors, year].filter(Boolean).join(" · ");

  return (
    <button
      type="button"
      onClick={onContinue}
      className="group flex w-full items-start gap-3 rounded-xl border border-primary/15 bg-primary/[0.03] px-3.5 py-3.5 text-left transition-[border-color,background-color] duration-200 hover:border-primary/25 hover:bg-primary/[0.045] dark:bg-primary/[0.06]"
    >
      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-[11px] font-medium uppercase tracking-[0.06em] text-text-tertiary">
          Continue reading
        </p>
        <p className="line-clamp-2 text-[14px] font-semibold leading-snug tracking-tight text-text-primary">
          {paperTitle(paper)}
        </p>
        {meta ? (
          <p className="truncate text-[12px] text-text-secondary">{meta}</p>
        ) : null}
        <p className="pt-0.5 text-[12px] text-text-tertiary">{paperStatusLabel(paper)}</p>
      </div>
      <span className="mt-0.5 inline-flex shrink-0 items-center gap-1 text-[12px] font-medium text-text-accent transition-transform duration-200 group-hover:translate-x-0.5">
        Continue
        <ArrowRight className="size-3.5 transition-transform duration-200 group-hover:translate-x-1" />
      </span>
    </button>
  );
}
