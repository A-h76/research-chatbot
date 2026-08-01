import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  PanelLeftClose,
  Library,
  Settings,
  Home,
  Plus,
  Search,
  FolderKanban,
  PenLine,
  StickyNote,
  Upload,
  Layers,
} from "lucide-react";
import { AccountMenu } from "./AccountMenu";
import {
  useUI,
  SIDEBAR_WIDTH_DEFAULT,
  SIDEBAR_WIDTH_MAX,
  SIDEBAR_WIDTH_MIN,
} from "@/context/UIContext";
import { useAllFiles } from "@/features/files/useFiles";
import { useProjects, useProjectHub } from "@/features/projects/useProjects";
import { isTypingTarget } from "@/lib/keyboard";
import { cn } from "@/lib/utils";
import type { Me, Project, UserFile } from "@/types/api";

const RESEARCH_LIST_LIMIT = 5;

/** Density bands for fluid sidebar content. */
export type SidebarDensity = "icons" | "labels" | "rich";

export function sidebarDensity(width: number): SidebarDensity {
  if (width < 268) return "icons";
  if (width < 340) return "labels";
  return "rich";
}

type ResearchStatus = "ready" | "review" | "idle";

function researchStatus(projectId: number, files: UserFile[]): ResearchStatus {
  const papers = files.filter((f) => f.kind === "document" && f.project_id === projectId);
  if (papers.length === 0) return "idle";
  const needsReview = papers.some(
    (p) =>
      p.reading_status === "unread" ||
      p.meta_status === "pending" ||
      p.meta_status === "running" ||
      p.meta_status === "failed",
  );
  return needsReview ? "review" : "ready";
}

function paperCountFor(projectId: number, files: UserFile[]): number {
  return files.filter((f) => f.kind === "document" && f.project_id === projectId).length;
}

const STATUS_DOT: Record<ResearchStatus, string> = {
  ready: "bg-emerald-500",
  review: "bg-amber-400",
  idle: "bg-muted-foreground/45",
};

const STATUS_LABEL: Record<ResearchStatus, string> = {
  ready: "Ready",
  review: "Needs review",
  idle: "Idle",
};

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
        "min-w-0 overflow-hidden whitespace-nowrap transition-[opacity,max-width] duration-200 ease-out",
        show ? "max-w-[14rem] opacity-100" : "max-w-0 opacity-0",
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
  active,
  onClick,
  trailing,
  density,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
  trailing?: React.ReactNode;
  density: SidebarDensity;
}) {
  const showLabel = density !== "icons";
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      className={cn(
        "group relative flex w-full items-center gap-2.5 rounded-md py-1.5 text-left text-[13px] transition-colors duration-200",
        density === "icons" ? "justify-center px-2" : "pr-2.5 pl-2.5",
        active
          ? "bg-sidebar-accent font-medium text-sidebar-foreground before:absolute before:inset-y-1 before:left-0 before:w-0.5 before:rounded-full before:bg-primary"
          : "font-normal text-muted-foreground hover:bg-sidebar-accent/70 hover:text-sidebar-foreground",
      )}
    >
      <span className="flex size-[22px] shrink-0 items-center justify-center text-muted-foreground [&_svg]:size-[18px]">
        {icon}
      </span>
      <FadeLabel show={showLabel} className="flex-1 truncate">
        {label}
      </FadeLabel>
      {showLabel && trailing}
    </button>
  );
}

function ResearchContextCard({
  projectId,
  density,
}: {
  projectId: number;
  density: SidebarDensity;
}) {
  const { data: hub } = useProjectHub(projectId);
  if (!hub || density !== "rich") return null;

  const papers = hub.stats.papers;
  const evidence = hub.stats.insights + hub.stats.open_questions;
  const writingReady = hub.pipeline_summary.done > 0 && hub.stats.papers > 0;

  return (
    <div className="mx-1 mt-1 rounded-md bg-sidebar-accent/60 px-2.5 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/80">
        Scope
      </p>
      <div className="mt-1.5 space-y-0.5 text-[11px] text-muted-foreground">
        <p>
          <span className="tabular-nums text-sidebar-foreground/90">{papers}</span> papers
        </p>
        <p>
          <span className="tabular-nums text-sidebar-foreground/90">{evidence}</span> evidence
          signals
        </p>
        <p className={writingReady ? "text-emerald-600 dark:text-emerald-400/90" : undefined}>
          {writingReady ? "Writing ready" : "Building corpus"}
        </p>
      </div>
    </div>
  );
}

/**
 * Places sidebar — Create · Home · Library · Search · Research · Settings.
 * Theme-aware · resizable · fluid density.
 */
export function SidebarContents({
  me,
  onNavigate,
  density = "labels",
}: {
  me: Me;
  onNavigate?: () => void;
  density?: SidebarDensity;
}) {
  const [createOpen, setCreateOpen] = useState(false);
  const { setActiveView, currentProjectId, setCurrentProjectId } = useUI();
  const navigate = useNavigate();
  const location = useLocation();
  const path = location.pathname;
  const showLabels = density !== "icons";
  const showMeta = density === "rich";

  const { data: projects = [] } = useProjects();
  const { data: files = [] } = useAllFiles();

  const routeProjectId = useMemo(() => {
    const m = path.match(/^\/projects\/(\d+)/);
    return m ? Number(m[1]) : null;
  }, [path]);

  const activeResearchId = routeProjectId ?? currentProjectId;

  const researchProjects = useMemo(() => {
    const sorted = [...projects].sort((a, b) => {
      if (a.id === activeResearchId) return -1;
      if (b.id === activeResearchId) return 1;
      return b.id - a.id;
    });
    return sorted.slice(0, RESEARCH_LIST_LIMIT);
  }, [projects, activeResearchId]);

  const isHome = path === "/home";
  const isLibrary =
    path.startsWith("/library") ||
    path.startsWith("/files") ||
    (path.startsWith("/papers/") && !path.includes("/chat"));
  const isSettings = path.startsWith("/settings");

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
      <div
        className={cn(
          "flex shrink-0 items-center gap-2.5 pt-5 pb-3",
          showLabels ? "justify-between px-4 pr-10" : "justify-center px-2",
        )}
      >
        <div className={cn("flex min-w-0 items-center gap-2.5", !showLabels && "justify-center")}>
          <div
            className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground transition-colors duration-200"
            title="Dhund — Research Operating System"
            aria-hidden
          >
            <span className="text-[10px] font-bold tracking-tight">Dh</span>
          </div>
          <FadeLabel show={showLabels}>
            <div className="min-w-0">
              <h1 className="truncate text-[14px] font-semibold tracking-tight text-sidebar-foreground">
                Dhund
              </h1>
              <p className="truncate text-[10px] text-muted-foreground">
                Research Operating System
              </p>
            </div>
          </FadeLabel>
        </div>
      </div>

      <nav className="lab-sidebar-scroll min-h-0 flex-1 space-y-5 overflow-y-auto px-2.5 pb-3">
        <div className="relative" data-create-menu>
          <button
            type="button"
            onClick={() => setCreateOpen((o) => !o)}
            title="Create"
            className={cn(
              "flex w-full items-center rounded-md py-1.5 text-sidebar-foreground transition-colors duration-200 hover:bg-sidebar-accent",
              showLabels ? "justify-between px-2.5" : "justify-center px-2",
            )}
            aria-expanded={createOpen}
            aria-haspopup="menu"
          >
            <span className="flex items-center gap-2.5 text-[13px] font-medium">
              <Plus className="size-[18px] shrink-0 text-muted-foreground" />
              <FadeLabel show={showLabels}>Create</FadeLabel>
            </span>
            {showLabels && (
              <kbd className="rounded px-1.5 py-0.5 text-[10px] text-muted-foreground/80">
                ⌘N
              </kbd>
            )}
          </button>
          {createOpen && (
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

        <div className="space-y-0.5">
          <PlaceItem
            density={density}
            icon={<Home />}
            label="Home"
            active={isHome}
            onClick={() => go("library", "/home")}
          />
          <PlaceItem
            density={density}
            icon={<Library />}
            label="Library"
            active={isLibrary}
            onClick={() => go("library", "/library")}
          />
          <PlaceItem
            density={density}
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

        {showLabels && (
          <div>
            <p className="mb-1 px-2.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/75">
              Research
            </p>
            <div className="space-y-0.5">
              {researchProjects.length === 0 ? (
                <button
                  type="button"
                  onClick={() => go("projects", "/projects?new=1")}
                  className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-[13px] text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
                >
                  <Plus className="size-4" />
                  Start a project
                </button>
              ) : (
                researchProjects.map((p) => {
                  const status = researchStatus(p.id, files);
                  const count = paperCountFor(p.id, files);
                  const active =
                    activeResearchId === p.id && path.startsWith("/projects/");
                  return (
                    <div key={p.id}>
                      <button
                        type="button"
                        title={`${p.name} · ${STATUS_LABEL[status]}`}
                        onClick={() => openProject(p)}
                        className={cn(
                          "group relative flex w-full items-center gap-2 rounded-md py-1.5 pr-2 pl-2.5 text-left text-[13px] transition-colors duration-200",
                          active
                            ? "bg-sidebar-accent font-medium text-sidebar-foreground before:absolute before:inset-y-1 before:left-0 before:w-0.5 before:rounded-full before:bg-primary"
                            : "text-muted-foreground hover:bg-sidebar-accent/70 hover:text-sidebar-foreground",
                        )}
                      >
                        <span
                          className={cn(
                            "size-1.5 shrink-0 rounded-full",
                            STATUS_DOT[status],
                          )}
                          aria-hidden
                        />
                        <span className="min-w-0 flex-1 truncate">
                          {p.emoji ? `${p.emoji} ` : ""}
                          {p.name}
                        </span>
                      </button>
                      {showMeta && (
                        <p className="truncate pl-6 text-[11px] text-muted-foreground/80">
                          {count} paper{count === 1 ? "" : "s"}
                          {active ? ` · ${STATUS_LABEL[status]}` : ""}
                        </p>
                      )}
                      {active && activeResearchId != null && (
                        <ResearchContextCard
                          projectId={activeResearchId}
                          density={density}
                        />
                      )}
                    </div>
                  );
                })
              )}
              {projects.length > 0 && (
                <button
                  type="button"
                  onClick={() => go("projects", "/projects")}
                  className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-[12px] text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
                >
                  <FolderKanban className="size-3.5 opacity-70" />
                  {projects.length > RESEARCH_LIST_LIMIT
                    ? "View all projects…"
                    : "All projects"}
                </button>
              )}
            </div>
          </div>
        )}

        {!showLabels && (
          <div className="space-y-0.5">
            {researchProjects.slice(0, 3).map((p) => {
              const status = researchStatus(p.id, files);
              const active =
                activeResearchId === p.id && path.startsWith("/projects/");
              return (
                <button
                  key={p.id}
                  type="button"
                  title={p.name}
                  onClick={() => openProject(p)}
                  className={cn(
                    "flex w-full items-center justify-center rounded-md py-1.5 transition-colors",
                    active
                      ? "bg-sidebar-accent"
                      : "hover:bg-sidebar-accent/70",
                  )}
                >
                  <span
                    className={cn("size-2 rounded-full", STATUS_DOT[status])}
                    aria-hidden
                  />
                </button>
              );
            })}
          </div>
        )}
      </nav>

      <div className="mt-auto shrink-0 space-y-0.5 border-t border-sidebar-border/60 p-2.5">
        <PlaceItem
          density={density}
          icon={<Settings />}
          label="Settings"
          active={isSettings}
          onClick={() => go("settings", "/settings")}
        />
        <AccountMenu me={me} compact={!showLabels} />
      </div>
    </div>
  );
}

function SidebarResizeHandle({
  onResize,
  disabled,
}: {
  onResize: (width: number) => void;
  disabled?: boolean;
}) {
  const dragging = useRef(false);
  const startX = useRef(0);
  const startW = useRef(SIDEBAR_WIDTH_DEFAULT);
  const { sidebarWidth } = useUI();

  useEffect(() => {
    if (disabled) return;

    const onMove = (e: PointerEvent) => {
      if (!dragging.current) return;
      const delta = e.clientX - startX.current;
      onResize(startW.current + delta);
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
  }, [disabled, onResize]);

  if (disabled) return null;

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-valuenow={sidebarWidth}
      aria-valuemin={SIDEBAR_WIDTH_MIN}
      aria-valuemax={SIDEBAR_WIDTH_MAX}
      aria-label="Resize sidebar"
      onPointerDown={(e) => {
        e.preventDefault();
        dragging.current = true;
        startX.current = e.clientX;
        startW.current = sidebarWidth;
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
      }}
      className={cn(
        "group/resize absolute inset-y-0 right-0 z-20 w-2 translate-x-1/2 cursor-col-resize",
        "flex items-center justify-center",
      )}
    >
      {/* Hover / drag grip — ⋮ style */}
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
  } = useUI();
  const [resizing, setResizing] = useState(false);
  const density = sidebarDensity(sidebarWidth);

  const handleResize = (w: number) => {
    setResizing(true);
    setSidebarWidth(w);
  };

  useEffect(() => {
    if (!resizing) return;
    const t = window.setTimeout(() => setResizing(false), 120);
    return () => window.clearTimeout(t);
  }, [sidebarWidth, resizing]);

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarCollapsed ? 0 : sidebarWidth }}
      transition={
        resizing
          ? { duration: 0 }
          : { duration: 0.2, ease: "easeInOut" }
      }
      className={cn(
        "relative hidden h-full min-h-0 shrink-0 self-stretch md:block",
        sidebarCollapsed ? "overflow-hidden" : "overflow-visible",
      )}
      style={
        {
          ["--sidebar-width" as string]: `${sidebarWidth}px`,
        } as React.CSSProperties
      }
    >
      <div
        className={cn(
          "dhund-sidebar absolute inset-y-0 left-0 flex min-h-0 flex-col overflow-hidden border-r border-sidebar-border",
          sidebarCollapsed && "pointer-events-none",
        )}
        style={{ width: sidebarWidth }}
      >
        <SidebarContents me={me} density={density} />
        <button
          type="button"
          onClick={() => setSidebarCollapsed(true)}
          title="Close sidebar (⌘B)"
          className={cn(
            "absolute top-3 z-10 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground",
            density === "icons" ? "right-0.5" : "right-2",
          )}
        >
          <PanelLeftClose className="size-4" />
        </button>
        {!sidebarCollapsed && (
          <SidebarResizeHandle
            onResize={(w) => {
              setResizing(true);
              handleResize(w);
            }}
          />
        )}
      </div>
    </motion.aside>
  );
}
