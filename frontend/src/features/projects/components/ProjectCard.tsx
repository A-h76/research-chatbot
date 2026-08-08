/**
 * Project row — bookshelf bookmark: what · where you stopped · what’s next.
 * Featured = Continue (one primary action); others defer with a quiet chevron.
 */
import { motion } from "framer-motion";
import { ArrowRight, ChevronRight, Pencil } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ProjectListRow } from "../projectsListViewModel";
import { papersPhrase } from "../projectsListViewModel";

export function ProjectCard({
  row,
  featured = false,
  onOpen,
  onEdit,
}: {
  row: ProjectListRow;
  featured?: boolean;
  onOpen: () => void;
  onEdit: () => void;
}) {
  const { project, papers, statusLabel, nextLabel, unlocksHint } = row;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
      className={cn(
        "group relative flex cursor-pointer items-start gap-3 text-left transition-[background-color,box-shadow,border-color] duration-200",
        featured
          ? "rounded-xl border border-primary/15 bg-primary/[0.03] px-3.5 py-3.5 hover:border-primary/25 hover:bg-primary/[0.045] dark:bg-primary/[0.06]"
          : "border-b border-border px-1 py-3 last:border-b-0 hover:bg-muted/25",
      )}
      data-density="high"
    >
      <div className="flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-background text-lg">
        {project.emoji}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start gap-2">
          <h3
            className={cn(
              "min-w-0 flex-1 truncate leading-snug tracking-tight text-text-primary",
              featured ? "text-[14px] font-semibold" : "text-[13px] font-medium",
            )}
          >
            {project.name}
          </h3>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="rounded-md p-1 text-text-tertiary opacity-0 transition-opacity hover:bg-muted hover:text-text-primary group-hover:opacity-100 focus-visible:opacity-100"
            title="Edit project"
          >
            <Pencil className="size-3.5" />
          </button>
        </div>

        <p className="mt-1 text-[12px] leading-relaxed text-text-secondary">
          {featured && nextLabel ? (
            <>
              Next milestone{" "}
              <span className="font-medium text-text-accent">{nextLabel}</span>
            </>
          ) : (
            <span>{statusLabel}</span>
          )}
        </p>

        {featured && unlocksHint ? (
          <p className="mt-1 text-[11px] leading-snug text-text-tertiary">{unlocksHint}</p>
        ) : null}

        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-text-secondary">
          <span className="tabular-nums">{papersPhrase(papers)}</span>
          {featured ? (
            <span className="text-text-tertiary">{statusLabel}</span>
          ) : null}
          {featured ? (
            <span className="ml-auto inline-flex items-center gap-1 font-medium text-text-accent transition-transform duration-200 group-hover:translate-x-0.5">
              Continue
              <ArrowRight className="size-3.5 transition-transform duration-200 group-hover:translate-x-1" />
            </span>
          ) : (
            <span
              className="ml-auto inline-flex items-center text-text-tertiary transition-colors group-hover:text-text-secondary"
              aria-hidden
            >
              <ChevronRight className="size-4" />
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
}
