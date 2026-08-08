import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  PanelLeftClose,
  Library,
  Settings,
  Home,
  Plus,
  Network,
  Search,
  FolderKanban,
  PenLine,
  StickyNote,
  Upload,
  Layers,
  FileText,
  FlaskConical,
  MessageSquare,
  Folder,
  ArrowLeft,
} from "lucide-react";
import { AccountMenu } from "./AccountMenu";
import {
  useUI,
  SIDEBAR_COLLAPSED_WIDTH,
  SIDEBAR_SNAP_COLLAPSE,
  SIDEBAR_WIDTH_DEFAULT,
  SIDEBAR_WIDTH_MAX,
  SIDEBAR_WIDTH_MIN,
} from "@/context/UIContext";
import { useProjects } from "@/features/projects/useProjects";
import {
  PROJECT_JOURNEY_SECONDARY,
  PROJECT_JOURNEY_WORKFLOW,
  isProjectWorkspacePath,
  resolveJourneyActive,
  type JourneyNavId,
} from "@/features/projects/projectWorkspaceNav";
import { isTypingTarget } from "@/lib/keyboard";
import { cn } from "@/lib/utils";
import type { Me, Project } from "@/types/api";

const JOURNEY_ICONS: Partial<Record<JourneyNavId, React.ReactNode>> = {
  papers: <FileText className="size-4" strokeWidth={1.5} />,
  research: <Network className="size-4" strokeWidth={1.5} />,
  writing: <PenLine className="size-4" strokeWidth={1.5} />,
  review: <FlaskConical className="size-4" strokeWidth={1.5} />,
  chat: <MessageSquare className="size-4" strokeWidth={1.5} />,
};

/** Density for expanded rail only (collapsed always clips labels). */
export type SidebarDensity = "labels" | "rich";

export function sidebarDensity(width: number): SidebarDensity {
  return width >= 240 ? "rich" : "labels";
}

/** Fixed icon column inset — never recenters when the rail folds. */
const ICON_INSET = "pl-3";

function FadeLabel({
  show,
  children,
  className,
}: {
  show: boolean;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "min-w-0 overflow-hidden whitespace-nowrap transition-[opacity,max-width,transform] duration-200 ease-out",
        show
          ? "max-w-[14rem] translate-x-0 opacity-100"
          : "max-w-0 -translate-x-1 opacity-0",
        className,
      )}
      aria-hidden={!show}
    >
      {children}
    </span>
  );
}

function PlaceItem({
  icon,
  label,
  title,
  active,
  emphasis,
  onClick,
  trailing,
  showLabel,
}: {
  icon: React.ReactNode;
  label: string;
  title?: string;
  active?: boolean;
  /** Project root — slightly stronger than journey children. */
  emphasis?: boolean;
  onClick: () => void;
  trailing?: React.ReactNode;
  showLabel: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title ?? label}
      className={cn(
        "group relative flex w-full items-center gap-2 rounded-md py-1.5 pr-2 text-left text-[13px] transition-colors duration-200",
        ICON_INSET,
        active
          ? "bg-sidebar-accent font-medium text-sidebar-foreground before:absolute before:inset-y-1 before:left-0 before:w-0.5 before:rounded-full before:bg-primary"
          : emphasis
            ? "font-medium text-sidebar-foreground/90 hover:bg-sidebar-accent/70 hover:text-sidebar-foreground"
            : "font-normal text-muted-foreground/80 hover:bg-sidebar-accent/70 hover:text-sidebar-foreground",
      )}
    >
      <span
        className={cn(
          "flex size-4 shrink-0 items-center justify-center [&_svg]:size-4",
          active || emphasis
            ? "text-primary"
            : "text-muted-foreground/45 group-hover:text-muted-foreground/70",
        )}
      >
        {icon}
      </span>
      <FadeLabel
        show={showLabel}
        className={cn("flex-1 truncate", emphasis && "font-semibold tracking-tight")}
      >
        {label}
      </FadeLabel>
      {showLabel ? trailing : null}
    </button>
  );
}

/**
 * Places sidebar — left-anchored icons; rail folds from the right (VS Code / Cursor).
 */
export function SidebarContents({
  me,
  onNavigate,
  showLabel,
}: {
  me: Me;
  onNavigate?: () => void;
  showLabel: boolean;
  /** Reserved for future rich meta density; accepted for API compatibility. */
  density?: SidebarDensity;
}) {
  const [createOpen, setCreateOpen] = useState(false);
  const { setActiveView, currentProjectId, setCurrentProjectId } = useUI();
  const navigate = useNavigate();
  const location = useLocation();
  const path = location.pathname;

  const { data: projects = [] } = useProjects();

  const routeProjectId = useMemo(() => {
    const m = path.match(/^\/projects\/(\d+)/);
    return m ? Number(m[1]) : null;
  }, [path]);

  const activeResearchId = routeProjectId ?? currentProjectId;

  const isHome = path === "/" || path === "/home";
  const isLibrary =
    path.startsWith("/library") ||
    path.startsWith("/files") ||
    (path.startsWith("/papers/") && !path.includes("/chat") && activeResearchId == null);
  const isSettings = path.startsWith("/settings");
  const isProjectsList = path === "/projects" || path === "/projects/";
  const inProjectShell =
    activeResearchId != null && isProjectWorkspacePath(path, activeResearchId);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target)) return;
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "n") {
        e.preventDefault();
        setCreateOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!createOpen) return;
    const onDoc = (e: MouseEvent) => {
      const t = e.target as HTMLElement | null;
      if (t?.closest?.("[data-create-menu]")) return;
      setCreateOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [createOpen]);

  function go(view: Parameters<typeof setActiveView>[0], next: string) {
    setActiveView(view);
    navigate(next);
    setCreateOpen(false);
  }

  function openProject(p: Project) {
    setCurrentProjectId(p.id);
    go("projects", `/projects/${p.id}`);
  }

  function openPalette() {
    setCreateOpen(false);
    window.dispatchEvent(new Event("soro:command-palette"));
  }

  return (
    <div className="flex h-full min-h-0 flex-col" onClickCapture={onNavigate}>
      <div className={cn("flex shrink-0 items-center gap-2 pt-4 pb-2.5 pr-9", ICON_INSET)}>
        <div className="flex min-w-0 items-center gap-2">
          <div
            className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground transition-colors duration-200"
            title="Dhund — Research Operating System"
            aria-hidden
          >
            <span className="text-[10px] font-bold tracking-tight">Dh</span>
          </div>
          <FadeLabel show={showLabel}>
            <div className="min-w-0">
              <h1 className="truncate text-[13px] font-semibold tracking-tight text-sidebar-foreground">
                Dhund
              </h1>
              <p className="truncate text-[10px] text-muted-foreground/80">
                Research OS
              </p>
            </div>
          </FadeLabel>
        </div>
      </div>

      <nav className="lab-sidebar-scroll min-h-0 flex-1 space-y-4 overflow-y-auto px-1.5 pb-3">
        <div className="relative" data-create-menu>
          <button
            type="button"
            onClick={() => setCreateOpen((o) => !o)}
            title="Create"
            className={cn(
              "flex w-full items-center gap-2 rounded-md py-1.5 pr-2 text-sidebar-foreground transition-colors duration-200 hover:bg-sidebar-accent",
              ICON_INSET,
            )}
            aria-expanded={createOpen}
            aria-haspopup="menu"
          >
            <Plus className="size-4 shrink-0 text-muted-foreground/50" />
            <FadeLabel show={showLabel} className="flex-1 text-[13px] font-medium">
              Create
            </FadeLabel>
            {showLabel && (
              <kbd className="rounded px-1 py-0.5 text-[10px] text-muted-foreground/70">
                ⌘N
              </kbd>
            )}
          </button>
          {createOpen && showLabel && (
            <div
              role="menu"
              className="absolute left-0 right-0 z-30 mt-1 rounded-lg border border-sidebar-border bg-popover py-1 text-popover-foreground shadow-lg"
            >
              {(
                [
                  {
                    label: "Project",
                    icon: FolderKanban,
                    run: () => go("projects", "/projects?new=1"),
                  },
                  {
                    label: "Writing",
                    icon: PenLine,
                    run: () => go("citations", "/writing"),
                  },
                  {
                    label: "Note",
                    icon: StickyNote,
                    run: () => go("memory", "/notes"),
                  },
                  {
                    label: "Import paper",
                    icon: Upload,
                    run: () => go("library", "/library?upload=1#import"),
                  },
                  {
                    label: "Collection",
                    icon: Layers,
                    run: () => go("library", "/library?collections=1"),
                  },
                ] as const
              ).map((item) => (
                <button
                  key={item.label}
                  type="button"
                  role="menuitem"
                  className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-[13px] hover:bg-sidebar-accent"
                  onClick={item.run}
                >
                  <item.icon className="size-4 text-muted-foreground" />
                  {item.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {inProjectShell && activeResearchId != null ? (
          <>
            <div className="space-y-0.5">
              <button
                type="button"
                title="Back to Home"
                onClick={() => go("library", "/")}
                className={cn(
                  "flex w-full items-center gap-2 rounded-md py-1.5 pr-2 text-left text-[12px] text-muted-foreground/75 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground",
                  ICON_INSET,
                )}
              >
                <ArrowLeft className="size-3.5 shrink-0 text-muted-foreground/50" />
                <FadeLabel show={showLabel}>Home</FadeLabel>
              </button>
            </div>

            <div>
              <FadeLabel show={showLabel}>
                <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
                  Project
                </p>
              </FadeLabel>
              <div className="space-y-0.5">
                {(() => {
                  const activeProject =
                    projects.find((p) => p.id === activeResearchId) ?? null;
                  const journeyActive = resolveJourneyActive(
                    path,
                    location.search,
                    activeResearchId,
                  );
                  return (
                    <>
                      <PlaceItem
                        showLabel={showLabel}
                        icon={<Folder />}
                        label={activeProject?.name ?? "Project"}
                        emphasis
                        active={
                          path === `/projects/${activeResearchId}` ||
                          path === `/projects/${activeResearchId}/`
                        }
                        onClick={() => {
                          const p = activeProject;
                          if (p) openProject(p);
                          else go("projects", `/projects/${activeResearchId}`);
                        }}
                      />
                      {[...PROJECT_JOURNEY_WORKFLOW, ...PROJECT_JOURNEY_SECONDARY].map(
                        (item) => (
                          <PlaceItem
                            key={item.id}
                            showLabel={showLabel}
                            icon={JOURNEY_ICONS[item.id] ?? <FileText />}
                            label={item.label}
                            title={item.title ?? item.label}
                            active={journeyActive === item.id}
                            onClick={() => {
                              setCurrentProjectId(activeResearchId);
                              navigate(item.href(activeResearchId));
                              setCreateOpen(false);
                            }}
                          />
                        ),
                      )}
                    </>
                  );
                })()}
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="space-y-0.5">
              <PlaceItem
                showLabel={showLabel}
                icon={<Home />}
                label="Home"
                active={isHome}
                onClick={() => go("library", "/")}
              />
              <PlaceItem
                showLabel={showLabel}
                icon={<FolderKanban />}
                label="Projects"
                active={isProjectsList}
                onClick={() => go("projects", "/projects")}
              />
              <PlaceItem
                showLabel={showLabel}
                icon={<Library />}
                label="Library"
                active={isLibrary}
                onClick={() => {
                  setCurrentProjectId(null);
                  go("library", "/library");
                }}
              />
              <PlaceItem
                showLabel={showLabel}
                icon={<Search />}
                label="Search"
                onClick={openPalette}
                trailing={
                  <kbd className="rounded px-1.5 py-0.5 text-[10px] text-muted-foreground/80">
                    ⌘K
                  </kbd>
                }
              />
            </div>
          </>
        )}
      </nav>

      <div className="mt-auto shrink-0 space-y-0.5 border-t border-sidebar-border/60 p-1.5 pt-2">
        <PlaceItem
          showLabel={showLabel}
          icon={<Settings />}
          label="Settings"
          active={isSettings}
          onClick={() => go("settings", "/settings")}
        />
        <AccountMenu me={me} compact={!showLabel} />
      </div>
    </div>
  );
}

function SidebarResizeHandle({
  onDragWidth,
}: {
  /** Live width from left edge of the shell to the pointer. */
  onDragWidth: (width: number) => void;
}) {
  const dragging = useRef(false);
  const { sidebarRailWidth } = useUI();

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      if (!dragging.current) return;
      // Sidebar is flush left — clientX is the target width.
      onDragWidth(e.clientX);
    };
    const onUp = () => {
      if (!dragging.current) return;
      dragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
  }, [onDragWidth]);

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-valuenow={sidebarRailWidth}
      aria-valuemin={SIDEBAR_COLLAPSED_WIDTH}
      aria-valuemax={SIDEBAR_WIDTH_MAX}
      aria-label="Resize sidebar"
      onPointerDown={(e) => {
        e.preventDefault();
        dragging.current = true;
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
      }}
      className={cn(
        "group/resize absolute inset-y-0 right-0 z-20 w-2 translate-x-1/2 cursor-col-resize",
        "flex items-center justify-center",
      )}
    >
      <div
        className={cn(
          "flex h-12 w-1 flex-col items-center justify-center gap-[3px] rounded-full",
          "bg-transparent opacity-0 transition-opacity duration-200",
          "group-hover/resize:bg-sidebar-border group-hover/resize:opacity-100",
          "group-active/resize:bg-primary/50 group-active/resize:opacity-100",
        )}
      >
        <span className="size-[3px] rounded-full bg-muted-foreground/70" />
        <span className="size-[3px] rounded-full bg-muted-foreground/70" />
        <span className="size-[3px] rounded-full bg-muted-foreground/70" />
      </div>
    </div>
  );
}

export function Sidebar({ me }: { me: Me }) {
  const {
    sidebarCollapsed,
    setSidebarCollapsed,
    sidebarWidth,
    setSidebarWidth,
    sidebarRailWidth,
  } = useUI();
  const [resizing, setResizing] = useState(false);
  const density = sidebarDensity(sidebarWidth);
  const showLabel = !sidebarCollapsed;

  const onDragWidth = useCallback(
    (width: number) => {
      setResizing(true);
      if (width < SIDEBAR_SNAP_COLLAPSE) {
        setSidebarCollapsed(true);
        return;
      }
      if (sidebarCollapsed) {
        setSidebarCollapsed(false);
      }
      // Between snap and min → park at min expanded; otherwise clamp.
      if (width < SIDEBAR_WIDTH_MIN) {
        setSidebarWidth(SIDEBAR_WIDTH_MIN);
        return;
      }
      setSidebarWidth(Math.min(SIDEBAR_WIDTH_MAX, Math.round(width)));
    },
    [setSidebarCollapsed, setSidebarWidth, sidebarCollapsed],
  );

  useEffect(() => {
    if (!resizing) return;
    const t = window.setTimeout(() => setResizing(false), 100);
    return () => window.clearTimeout(t);
  }, [sidebarRailWidth, resizing]);

  // Layout width stays at the expanded size so icons don't shift while the rail folds.
  const contentWidth = Math.max(sidebarWidth, SIDEBAR_WIDTH_DEFAULT);

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarRailWidth }}
      transition={
        resizing ? { duration: 0 } : { duration: 0.22, ease: [0.22, 1, 0.36, 1] }
      }
      className={cn(
        "relative hidden h-full min-h-0 shrink-0 self-stretch md:block",
        "overflow-visible",
      )}
      style={
        {
          ["--sidebar-width" as string]: `${sidebarRailWidth}px`,
        } as React.CSSProperties
      }
    >
      <div
        className="dhund-sidebar absolute inset-y-0 left-0 flex min-h-0 flex-col overflow-hidden border-r border-sidebar-border"
        style={{ width: sidebarRailWidth }}
      >
        {/* Fixed left layout; rail clips from the right when collapsing. */}
        <div className="h-full min-h-0" style={{ width: contentWidth }}>
          <SidebarContents me={me} showLabel={showLabel} density={density} />
        </div>

        {!sidebarCollapsed && (
          <button
            type="button"
            onClick={() => setSidebarCollapsed(true)}
            title="Collapse sidebar (⌘B)"
            className="absolute top-3 right-1.5 z-10 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
          >
            <PanelLeftClose className="size-4" />
          </button>
        )}

        <SidebarResizeHandle onDragWidth={onDragWidth} />
      </div>
    </motion.aside>
  );
}
