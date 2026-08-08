/**
 * Project row — bookshelf bookmark: what · where you stopped · what’s next.
 * Featured = Continue Research; others = quieter Open.
 * Outcome-oriented copy — no stage-machine jargon dump.
 */
import { motion } from "framer-motion";
import { ArrowRight, Pencil } from "lucide-react";
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
  const cta = featured ? "Continue" : "Open";

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
        "group relative flex cursor-pointer items-start gap-3 px-1 py-4 text-left transition-[background-color,transform] duration-200",
        featured
          ? "rounded-2xl border border-primary/20 bg-[linear-gradient(180deg,color-mix(in_oklab,var(--primary)_5%,white)_0%,transparent_100%)] px-4 shadow-[0_1px_2px_rgba(15,23,42,0.03),0_8px_20px_-14px_rgba(15,110,106,0.22)] hover:-translate-y-0.5 dark:bg-[linear-gradient(180deg,color-mix(in_oklab,var(--primary)_12%,transparent)_0%,transparent_100%)]"
          : "border-b border-border last:border-b-0 hover:bg-muted/25",
      )}
      data-density="high"
    >
      <div className="flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-background text-lg">
        {project.emoji}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start gap-2">
          <h3 className="min-w-0 flex-1 truncate text-[14px] font-semibold leading-snug tracking-tight text-text-primary">
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
            <span className="text-text-primary/90">{statusLabel}</span>
          )}
        </p>

        {featured && unlocksHint ? (
          <p className="mt-1 text-[11px] text-text-tertiary">{unlocksHint}</p>
        ) : null}

        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-text-secondary">
          <span className="tabular-nums">{papersPhrase(papers)}</span>
          {featured ? (
            <span className="text-text-tertiary">{statusLabel}</span>
          ) : null}
          <span className="ml-auto inline-flex items-center gap-1 font-medium text-text-accent transition-transform duration-200 group-hover:translate-x-0.5">
            {cta}
            <ArrowRight className="size-3.5 transition-transform duration-200 group-hover:translate-x-1" />
          </span>
        </div>
      </div>
    </motion.div>
  );
}
