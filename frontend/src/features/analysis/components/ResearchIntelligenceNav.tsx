import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import {
  RI_OVERVIEW,
  categoryForTab,
  navCategories,
  questionForTab,
  type RiCategoryId,
  type RiTab,
} from "../researchIntelligenceNav";
import { cn } from "@/lib/utils";

/**
 * Workflow-oriented RI chrome: Overview + category dropdowns.
 * Parent label → category landing; children → lenses.
 */
export function ResearchIntelligenceNav({
  tab,
  onOpenTab,
  showCompare,
}: {
  tab: RiTab;
  onOpenTab: (next: RiTab) => void;
  showCompare: boolean;
}) {
  const [openId, setOpenId] = useState<RiCategoryId | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const activeCategory = categoryForTab(tab);
  const categories = navCategories(showCompare);
  const question = questionForTab(tab);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpenId(null);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpenId(null);
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  return (
    <div className="mb-3 space-y-2 border-b border-border/70 pb-0" ref={rootRef}>
      <nav
        className="flex flex-wrap items-center gap-0.5"
        aria-label="Research Intelligence workflow"
      >
        <button
          type="button"
          onClick={() => {
            setOpenId(null);
            onOpenTab("overview");
          }}
          className={cn(
            "relative inline-flex h-9 items-center gap-1.5 px-2.5 text-[12px] font-medium",
            tab === "overview"
              ? "text-foreground after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:rounded-full after:bg-primary"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          <RI_OVERVIEW.icon className="size-3.5 shrink-0" />
          <span>{RI_OVERVIEW.label}</span>
        </button>

        {categories.map((cat) => {
          const isCategoryActive = activeCategory === cat.id;
          const menuOpen = openId === cat.id;
          return (
            <div key={cat.id} className="relative">
              <div
                className={cn(
                  "relative inline-flex h-9 items-stretch",
                  isCategoryActive &&
                    "after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:rounded-full after:bg-primary",
                )}
              >
                <button
                  type="button"
                  onClick={() => {
                    setOpenId(null);
                    onOpenTab(cat.id);
                  }}
                  className={cn(
                    "inline-flex items-center gap-1.5 pl-2.5 pr-1 text-[12px] font-medium",
                    isCategoryActive
                      ? "text-foreground"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <span>{cat.label}</span>
                </button>
                <button
                  type="button"
                  aria-expanded={menuOpen}
                  aria-haspopup="menu"
                  aria-label={`${cat.label} lenses`}
                  onClick={() => setOpenId((prev) => (prev === cat.id ? null : cat.id))}
                  className={cn(
                    "inline-flex items-center pr-2 text-muted-foreground hover:text-foreground",
                    isCategoryActive && "text-foreground",
                  )}
                >
                  <ChevronDown
                    className={cn("size-3.5 transition-transform", menuOpen && "rotate-180")}
                  />
                </button>
              </div>

              {menuOpen ? (
                <div
                  role="menu"
                  className="absolute left-0 top-full z-40 mt-1 min-w-[13rem] rounded-lg border border-border bg-card py-1 shadow-md"
                >
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setOpenId(null);
                      onOpenTab(cat.id);
                    }}
                    className={cn(
                      "flex w-full items-center gap-2 px-3 py-2 text-left text-[12px]",
                      tab === cat.id
                        ? "bg-muted/60 font-medium text-foreground"
                        : "text-foreground hover:bg-muted/50",
                    )}
                  >
                    {cat.label} overview
                  </button>
                  {cat.children.length ? (
                    <div className="my-1 border-t border-border" />
                  ) : (
                    <p className="px-3 py-2 text-[11px] text-muted-foreground">
                      More synthesis tools coming — start from the overview.
                    </p>
                  )}
                  {cat.children.map((child) => {
                    const Icon = child.icon;
                    return (
                      <button
                        key={child.key}
                        type="button"
                        role="menuitem"
                        onClick={() => {
                          setOpenId(null);
                          onOpenTab(child.key);
                        }}
                        className={cn(
                          "flex w-full items-center gap-2 px-3 py-2 text-left text-[12px]",
                          tab === child.key
                            ? "bg-muted/60 font-medium text-foreground"
                            : "text-foreground hover:bg-muted/50",
                        )}
                      >
                        <Icon className="size-3.5 shrink-0 text-muted-foreground" />
                        {child.label}
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          );
        })}
      </nav>
      {question ? (
        <p className="px-1 pb-2 text-[12px] text-muted-foreground">{question}</p>
      ) : null}
    </div>
  );
}
