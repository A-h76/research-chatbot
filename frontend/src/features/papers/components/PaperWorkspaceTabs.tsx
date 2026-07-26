import { cn } from "@/lib/utils";
import {
  PAPER_TABS,
  PAPER_TAB_LABELS,
  paperTabPanelId,
  paperTabTriggerId,
  type PaperTabId,
} from "../tabs";

export function PaperWorkspaceTabList({
  active,
  onSelect,
}: {
  active: PaperTabId;
  onSelect: (tab: PaperTabId) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Paper workspace"
      className="flex gap-1 overflow-x-auto border-b border-border pb-px scrollbar-thin"
    >
      {PAPER_TABS.map((tab) => {
        const selected = active === tab;
        return (
          <button
            key={tab}
            type="button"
            role="tab"
            id={paperTabTriggerId(tab)}
            aria-selected={selected}
            aria-controls={paperTabPanelId(tab)}
            tabIndex={selected ? 0 : -1}
            onClick={() => onSelect(tab)}
            onKeyDown={(e) => {
              const i = PAPER_TABS.indexOf(tab);
              if (e.key === "ArrowRight") {
                e.preventDefault();
                onSelect(PAPER_TABS[(i + 1) % PAPER_TABS.length]!);
              } else if (e.key === "ArrowLeft") {
                e.preventDefault();
                onSelect(PAPER_TABS[(i - 1 + PAPER_TABS.length) % PAPER_TABS.length]!);
              } else if (e.key === "Home") {
                e.preventDefault();
                onSelect(PAPER_TABS[0]!);
              } else if (e.key === "End") {
                e.preventDefault();
                onSelect(PAPER_TABS[PAPER_TABS.length - 1]!);
              }
            }}
            className={cn(
              "shrink-0 px-3 py-2 text-[13px] font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              selected
                ? "border-b-2 border-primary text-primary"
                : "border-b-2 border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {PAPER_TAB_LABELS[tab]}
          </button>
        );
      })}
    </div>
  );
}

export function PaperTabPanel({
  tab,
  active,
  children,
}: {
  tab: PaperTabId;
  active: PaperTabId;
  children: React.ReactNode;
}) {
  if (tab !== active) return null;
  return (
    <div
      role="tabpanel"
      id={paperTabPanelId(tab)}
      aria-labelledby={paperTabTriggerId(tab)}
      tabIndex={0}
      className="outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-md"
    >
      {children}
    </div>
  );
}
