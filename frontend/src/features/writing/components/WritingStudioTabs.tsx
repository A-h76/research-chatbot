import { cn } from "@/lib/utils";

export type WritingStudioTabId = "manuscript" | "notes" | "outline" | "export";

const TABS: { id: WritingStudioTabId; label: string }[] = [
  { id: "manuscript", label: "Manuscript" },
  { id: "notes", label: "Notes" },
  { id: "outline", label: "Outline" },
];

export function WritingStudioTabs({
  active,
  onChange,
  showExport,
  onExport,
}: {
  active: WritingStudioTabId;
  onChange: (tab: WritingStudioTabId) => void;
  showExport?: boolean;
  onExport?: () => void;
}) {
  return (
    <div
      className="flex shrink-0 items-center gap-0.5 border-b border-border/50 px-0.5"
      role="tablist"
      aria-label="Writing workspace"
    >
      {TABS.map((t) => (
        <button
          key={t.id}
          type="button"
          role="tab"
          aria-selected={active === t.id}
          onClick={() => onChange(t.id)}
          className={cn(
            "border-b-2 px-3 py-2 text-[13px] font-medium transition-colors",
            active === t.id
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground/80 hover:text-foreground",
          )}
        >
          {t.label}
        </button>
      ))}
      {showExport && onExport ? (
        <button
          type="button"
          role="tab"
          aria-selected={active === "export"}
          onClick={onExport}
          className={cn(
            "ml-auto border-b-2 px-3 py-2 text-[13px] font-medium transition-colors",
            active === "export"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground/80 hover:text-foreground",
          )}
        >
          Export
        </button>
      ) : null}
    </div>
  );
}
