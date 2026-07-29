/**
 * Left rail: literature-review outline → selects section type for grounded generate.
 */
import { History } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  WRITING_SECTION_OPTIONS,
  type WritingSectionType,
} from "@/features/evidence/hooks/useGroundedWriting";

const WORKFLOW = [
  "Outline",
  "Evidence",
  "Write",
  "Verify",
  "Accept",
  "Export",
] as const;

type VersionItem = {
  id: number;
  version_no: number;
  source: string;
  created_at?: string | null;
};

type Props = {
  sectionType: WritingSectionType;
  onSectionTypeChange: (next: WritingSectionType) => void;
  versions?: VersionItem[];
  onRestoreVersion?: (versionId: number) => void;
  className?: string;
};

export function WritingOutlineRail({
  sectionType,
  onSectionTypeChange,
  versions = [],
  onRestoreVersion,
  className,
}: Props) {
  return (
    <aside
      className={cn(
        "flex min-h-0 flex-col gap-3 rounded-lg border border-border bg-muted/20 p-3",
        className,
      )}
      aria-label="Outline"
    >
      <div>
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Workflow
        </p>
        <ol className="mt-1.5 space-y-0.5">
          {WORKFLOW.map((step, i) => (
            <li
              key={step}
              className="flex items-center gap-1.5 text-[11px] text-muted-foreground"
            >
              <span className="tabular-nums text-[10px] opacity-60">{i + 1}.</span>
              {step}
            </li>
          ))}
        </ol>
      </div>

      <div>
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Outline
        </p>
        <p className="mt-0.5 text-[10px] text-muted-foreground">
          Select a section, then generate from evidence
        </p>
        <ul className="mt-2 space-y-0.5" role="listbox" aria-label="Section outline">
          {WRITING_SECTION_OPTIONS.map((opt) => {
            const selected = sectionType === opt.value;
            return (
              <li key={opt.value}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => onSectionTypeChange(opt.value)}
                  className={cn(
                    "flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-[12px] transition-colors",
                    selected
                      ? "bg-primary/15 font-medium text-primary"
                      : "text-foreground hover:bg-muted/60",
                  )}
                >
                  <span className="truncate">{opt.label}</span>
                  {opt.experimental ? (
                    <span className="ml-1 shrink-0 text-[9px] uppercase text-muted-foreground">
                      exp
                    </span>
                  ) : null}
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="min-h-0 flex-1 border-t border-border pt-2">
        <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
          <History className="size-3.5" aria-hidden />
          Versions
        </div>
        <div className="max-h-40 overflow-auto">
          {versions.map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => onRestoreVersion?.(v.id)}
              className="mb-1 flex w-full items-center justify-between rounded border border-border px-2 py-1 text-left text-[11px] hover:bg-muted/40"
            >
              <span>
                v{v.version_no} · {v.source}
              </span>
              <span className="text-muted-foreground">
                {v.created_at ? new Date(v.created_at).toLocaleTimeString() : ""}
              </span>
            </button>
          ))}
          {!versions.length && (
            <p className="px-1 py-1 text-[11px] text-muted-foreground">No versions yet</p>
          )}
        </div>
      </div>
    </aside>
  );
}
