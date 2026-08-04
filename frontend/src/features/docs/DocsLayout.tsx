import { useEffect, useMemo, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { ArrowLeft, BookOpen, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { DOCS_NAV, type DocsNavGroup } from "./catalog";
import type { TocHeading } from "./toc";

type Props = {
  title: string;
  description?: string;
  toc: TocHeading[];
  /** Remount TOC observer when the page slug changes. */
  contentKey?: string;
  children: React.ReactNode;
};

/**
 * Mintlify-inspired docs shell: sidebar · prose · TOC.
 * Accent stays Dhund signal teal (Design Language v1).
 */
export function DocsLayout({ title, description, toc, contentKey, children }: Props) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    setActiveId("");
    if (toc.length === 0) return;

    let observer: IntersectionObserver | null = null;
    const frame = window.requestAnimationFrame(() => {
      const elements = toc
        .map((h) => document.getElementById(h.id))
        .filter((el): el is HTMLElement => Boolean(el));
      if (elements.length === 0) return;

      observer = new IntersectionObserver(
        (entries) => {
          const visible = entries
            .filter((e) => e.isIntersecting)
            .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
          if (visible[0]?.target?.id) setActiveId(visible[0].target.id);
        },
        { rootMargin: "-20% 0px -65% 0px", threshold: [0, 1] },
      );
      for (const el of elements) observer.observe(el);
    });

    return () => {
      window.cancelAnimationFrame(frame);
      observer?.disconnect();
    };
  }, [toc, contentKey]);

  const tocItems = useMemo(() => toc.filter((h) => h.level === 2 || h.level === 3), [toc]);

  return (
    <div className="min-h-screen bg-background text-foreground" data-density="medium">
      <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-3 px-4 sm:px-6">
          <button
            type="button"
            className="inline-flex size-9 items-center justify-center rounded-md border border-border lg:hidden"
            aria-label={mobileNavOpen ? "Close docs menu" : "Open docs menu"}
            aria-expanded={mobileNavOpen}
            onClick={() => setMobileNavOpen((v) => !v)}
          >
            {mobileNavOpen ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
          <Link to="/docs" className="flex items-center gap-2 text-sm font-semibold tracking-tight">
            <span className="flex size-7 items-center justify-center rounded-md border border-border bg-card">
              <BookOpen className="size-3.5 text-primary" aria-hidden />
            </span>
            Dhund Docs
          </Link>
          <span className="hidden text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground sm:inline">
            Contracts · API · ADRs
          </span>
          <Link
            to="/"
            className="ml-auto inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" />
            Back to app
          </Link>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1440px] lg:grid-cols-[240px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)_200px]">
        <aside
          className={cn(
            "border-border bg-background lg:sticky lg:top-14 lg:block lg:max-h-[calc(100vh-3.5rem)] lg:overflow-y-auto lg:border-r lg:px-4 lg:py-6",
            mobileNavOpen
              ? "fixed inset-x-0 top-14 z-20 max-h-[calc(100vh-3.5rem)] overflow-y-auto border-b px-4 py-4 shadow-sm"
              : "hidden",
          )}
          aria-label="Documentation"
        >
          <DocsSidebar nav={DOCS_NAV} onNavigate={() => setMobileNavOpen(false)} />
        </aside>

        <main className="min-w-0 px-4 py-8 sm:px-8 lg:px-10 lg:py-10">
          <p className="mb-2 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
            Documentation
          </p>
          <h1 className="text-[1.65rem] font-semibold tracking-tight text-foreground sm:text-[1.85rem]">
            {title}
          </h1>
          {description ? (
            <p className="mt-2 max-w-[65ch] text-[15px] leading-relaxed text-muted-foreground">
              {description}
            </p>
          ) : null}
          <div className="mt-8 max-w-[65ch]">{children}</div>
        </main>

        <nav
          className="sticky top-14 hidden max-h-[calc(100vh-3.5rem)] overflow-y-auto border-l border-border px-4 py-8 xl:block"
          aria-label="On this page"
        >
          {tocItems.length > 0 ? (
            <>
              <p className="mb-3 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
                On this page
              </p>
              <ul className="space-y-1.5 text-[12px] leading-snug">
                {tocItems.map((h) => (
                  <li key={h.id} className={cn(h.level === 3 && "pl-3")}>
                    <a
                      href={`#${h.id}`}
                      className={cn(
                        "block text-muted-foreground transition-colors hover:text-foreground",
                        activeId === h.id && "font-medium text-primary",
                      )}
                    >
                      {h.text}
                    </a>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-[12px] text-muted-foreground">No sections</p>
          )}
        </nav>
      </div>
    </div>
  );
}

function DocsSidebar({
  nav,
  onNavigate,
}: {
  nav: DocsNavGroup[];
  onNavigate?: () => void;
}) {
  return (
    <nav className="space-y-6">
      {nav.map((group) => (
        <div key={group.title}>
          <p className="mb-2 px-2 text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
            {group.title}
          </p>
          <ul className="space-y-0.5">
            {group.items.map((item) => (
              <li key={item.slug}>
                <NavLink
                  to={`/docs/${item.slug}`}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    cn(
                      "block rounded-md px-2 py-1.5 text-[13px] leading-snug transition-colors",
                      isActive
                        ? "bg-accent-soft/80 font-medium text-foreground"
                        : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                    )
                  }
                >
                  {item.title}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
