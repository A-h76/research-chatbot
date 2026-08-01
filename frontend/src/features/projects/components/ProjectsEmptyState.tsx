import { Check, ChevronRight, FileText, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { UserFile } from "@/types/api";

const LOOP = ["Papers", "Questions", "Evidence", "Writing", "Exports"] as const;

export function ProjectsEmptyState({
  papers,
  selectedIds,
  onToggle,
  onCreate,
}: {
  papers: UserFile[];
  selectedIds: Set<number>;
  onToggle: (id: number) => void;
  onCreate: () => void;
}) {
  const hasPapers = papers.length > 0;
  const selectedCount = selectedIds.size;

  return (
    <div className="mx-auto flex max-w-lg flex-col items-center py-10 text-center sm:py-14">
      {/* Mental model — why Projects exist */}
      <div
        className="mb-8 flex flex-wrap items-center justify-center gap-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground"
        aria-label="How a research project is organised"
      >
        {LOOP.map((step, i) => (
          <span key={step} className="flex items-center gap-1">
            {i > 0 && <ChevronRight className="size-3 opacity-40" aria-hidden />}
            <span
              className={cn(
                "rounded-md px-2 py-1",
                i === 0 ? "bg-muted text-foreground" : "bg-muted/50",
              )}
            >
              {step}
            </span>
          </span>
        ))}
      </div>

      <div className="mb-5 flex size-14 items-center justify-center rounded-2xl border border-border bg-muted/40">
        <div className="flex flex-col items-center gap-0.5 text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">
          <span className="text-primary">Project</span>
          <span className="h-px w-8 bg-border" />
          <span>Papers</span>
          <span className="h-px w-6 bg-border" />
          <span>Evidence</span>
        </div>
      </div>

      <h2 className="text-lg font-semibold tracking-tight text-foreground">
        No projects yet
      </h2>
      <p className="mt-2 max-w-sm text-[13px] leading-relaxed text-muted-foreground">
        Projects organise papers, evidence, questions, and writing into one workspace —
        not a pile of PDFs.
      </p>

      {hasPapers && (
        <div className="mt-7 w-full text-left">
          <p className="mb-2 text-center text-[12px] text-muted-foreground">
            You already imported {papers.length === 1 ? "a paper" : `${papers.length} papers`}.
            {selectedCount > 0
              ? ` Create a project from ${selectedCount === 1 ? "it" : "them"}.`
              : " Select papers to include, or create an empty project."}
          </p>
          <ul className="overflow-hidden rounded-xl border border-border bg-card">
            {papers.map((p) => {
              const selected = selectedIds.has(p.id);
              const title = p.title || p.name;
              return (
                <li key={p.id} className="border-b border-border last:border-b-0">
                  <button
                    type="button"
                    onClick={() => onToggle(p.id)}
                    className={cn(
                      "flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors",
                      selected ? "bg-primary/5" : "hover:bg-muted/40",
                    )}
                    aria-pressed={selected}
                  >
                    <span
                      className={cn(
                        "flex size-5 shrink-0 items-center justify-center rounded-md border",
                        selected
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-border bg-background text-transparent",
                      )}
                    >
                      <Check className="size-3" strokeWidth={3} />
                    </span>
                    <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-foreground">
                      {title}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <Button size="lg" className="mt-7 gap-1.5" onClick={onCreate}>
        <Plus className="size-4" />
        {hasPapers && selectedCount > 0
          ? "Create project"
          : "Create first project"}
      </Button>
    </div>
  );
}
