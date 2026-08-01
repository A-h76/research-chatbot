import { useEffect, useMemo, useState } from "react";
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
import { useUI } from "@/context/UIContext";
import { useAllFiles } from "@/features/files/useFiles";
import { useProjects, useProjectHub } from "@/features/projects/useProjects";
import { isTypingTarget } from "@/lib/keyboard";
import { cn } from "@/lib/utils";
import type { Me, Project, UserFile } from "@/types/api";

const SIDEBAR_WIDTH = 280;
const RESEARCH_LIST_LIMIT = 5;

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

function PlaceItem({
  icon,
  label,
  active,
  onClick,
  trailing,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
  trailing?: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group relative flex w-full items-center gap-2.5 rounded-md py-1.5 pr-2.5 pl-2.5 text-left text-[13px] transition-colors",
        active
          ? "bg-[#232933] font-medium text-sidebar-foreground before:absolute before:inset-y-1 before:left-0 before:w-0.5 before:rounded-full before:bg-primary"
          : "font-normal text-muted-foreground hover:bg-[#181C22] hover:text-sidebar-foreground",
      )}
    >
      <span className="flex size-[22px] shrink-0 items-center justify-center text-muted-foreground [&_svg]:size-[18px]">
        {icon}
      </span>
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {trailing}
    </button>
  );
}

function ResearchContextCard({ projectId }: { projectId: number }) {
  const { data: hub } = useProjectHub(projectId);
  if (!hub) return null;

  const papers = hub.stats.papers;
  const evidence = hub.stats.insights + hub.stats.open_questions;
  const writingReady = hub.pipeline_summary.done > 0 && hub.stats.papers > 0;

  return (
    <div className="mx-1 mt-1 rounded-md border border-sidebar-border/70 bg-[#181C22]/80 px-2.5 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/80">
        Scope
      </p>
      <div className="mt-1.5 space-y-0.5 text-[11px] text-muted-foreground">
        <p>
          <span className="tabular-nums text-sidebar-foreground/90">{papers}</span> papers
        </p>
        <p>
          <span className="tabular-nums text-sidebar-foreground/90">{evidence}</span> evidence signals
        </p>
        <p className={writingReady ? "text-emerald-400/90" : undefined}>
          {writingReady ? "Writing ready" : "Building corpus"}
        </p>
      </div>
    </div>
  );
}

/**
 * Places sidebar — Create · Home · Library · Search · Research · Settings.
 * Actions live in ⌘K; features live inside pages.
 */
export function SidebarContents({
  me,
  onNavigate,
}: {
  me: Me;
  onNavigate?: () => void;
}) {
  const [createOpen, setCreateOpen] = useState(false);
  const { setActiveView, currentProjectId, setCurrentProjectId } = useUI();
  const navigate = useNavigate();
  const location = useLocation();
  const path = location.pathname;

  const { data: projects = [] } = useProjects();
  const { data: files = [] } = useAllFiles();

  const routeProjectId = useMemo(() => {
    const m = path.match(/^\/projects\/(\d+)/);
    return m ? Number(m[1]) : null;
  }, [path]);

  const activeResearchId = routeProjectId ?? currentProjectId;

  const researchProjects = useMemo(() => {
    // Prefer current/route project first, then rest by id (stable).
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
    <div className="flex h-full flex-col" onClickCapture={onNavigate}>
      <div className="flex items-center justify-between gap-2 px-4 pt-5 pb-3 pr-10">
        <div className="flex min-w-0 items-center gap-2.5">
          <div
            className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/90 text-primary-foreground"
            title="Dhund — Research Operating System"
            aria-hidden
          >
            <span className="text-[10px] font-bold tracking-tight">Dh</span>
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-[14px] font-semibold tracking-tight text-sidebar-foreground">
              Dhund
            </h1>
            <p className="truncate text-[10px] text-muted-foreground">
              Research Operating System
            </p>
          </div>
        </div>
      </div>

      <nav className="lab-sidebar-scroll flex-1 space-y-5 overflow-y-auto px-2.5 pb-3">
        {/* Create */}
        <div className="relative" data-create-menu>
          <button
            type="button"
            onClick={() => setCreateOpen((o) => !o)}
            className="flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-sidebar-foreground transition-colors hover:bg-[#181C22]"
            aria-expanded={createOpen}
            aria-haspopup="menu"
          >
            <span className="flex items-center gap-2.5 text-[13px] font-medium">
              <Plus className="size-[18px] text-muted-foreground" />
              Create
            </span>
            <kbd className="rounded px-1.5 py-0.5 text-[10px] text-muted-foreground/80">
              ⌘N
            </kbd>
          </button>
          {createOpen && (
            <div
              role="menu"
              className="absolute left-0 right-0 z-30 mt-1 rounded-lg border border-sidebar-border bg-[#181C22] py-1 shadow-xl"
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
                  className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-[13px] text-sidebar-foreground hover:bg-[#232933]"
                  onClick={item.run}
                >
                  <item.icon className="size-4 text-muted-foreground" />
                  {item.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Places */}
        <div className="space-y-0.5">
          <PlaceItem
            icon={<Home />}
            label="Home"
            active={isHome}
            onClick={() => go("library", "/home")}
          />
          <PlaceItem
            icon={<Library />}
            label="Library"
            active={isLibrary}
            onClick={() => go("library", "/library")}
          />
          <PlaceItem
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

        {/* Research sessions */}
        <div>
          <p className="mb-1 px-2.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/75">
            Research
          </p>
          <div className="space-y-0.5">
            {researchProjects.length === 0 ? (
              <button
                type="button"
                onClick={() => go("projects", "/projects?new=1")}
                className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-[13px] text-muted-foreground hover:bg-[#181C22] hover:text-sidebar-foreground"
              >
                <Plus className="size-4" />
                Start a project
              </button>
            ) : (
              researchProjects.map((p) => {
                const status = researchStatus(p.id, files);
                const active = activeResearchId === p.id && path.startsWith("/projects/");
                return (
                  <div key={p.id}>
                    <button
                      type="button"
                      title={`${p.name} · ${STATUS_LABEL[status]}`}
                      onClick={() => openProject(p)}
                      className={cn(
                        "group relative flex w-full items-center gap-2 rounded-md py-1.5 pr-2 pl-2.5 text-left text-[13px] transition-colors",
                        active
                          ? "bg-[#232933] font-medium text-sidebar-foreground before:absolute before:inset-y-1 before:left-0 before:w-0.5 before:rounded-full before:bg-primary"
                          : "text-muted-foreground hover:bg-[#181C22] hover:text-sidebar-foreground",
                      )}
                    >
                      <span
                        className={cn("size-1.5 shrink-0 rounded-full", STATUS_DOT[status])}
                        aria-hidden
                      />
                      <span className="min-w-0 flex-1 truncate">
                        {p.emoji ? `${p.emoji} ` : ""}
                        {p.name}
                      </span>
                    </button>
                    {active && activeResearchId != null && (
                      <ResearchContextCard projectId={activeResearchId} />
                    )}
                  </div>
                );
              })
            )}
            {projects.length > 0 && (
              <button
                type="button"
                onClick={() => go("projects", "/projects")}
                className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-[12px] text-muted-foreground hover:bg-[#181C22] hover:text-sidebar-foreground"
              >
                <FolderKanban className="size-3.5 opacity-70" />
                {projects.length > RESEARCH_LIST_LIMIT
                  ? "View all projects…"
                  : "All projects"}
              </button>
            )}
          </div>
        </div>
      </nav>

      <div className="space-y-0.5 border-t border-sidebar-border/80 p-2.5">
        <PlaceItem
          icon={<Settings />}
          label="Settings"
          active={isSettings}
          onClick={() => go("settings", "/settings")}
        />
        <AccountMenu me={me} />
      </div>
    </div>
  );
}

export function Sidebar({ me }: { me: Me }) {
  const { sidebarCollapsed, setSidebarCollapsed } = useUI();

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarCollapsed ? 0 : SIDEBAR_WIDTH }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="relative hidden shrink-0 overflow-hidden md:block"
    >
      <div className="dhund-lab-sidebar absolute inset-y-0 left-0 flex w-[280px] flex-col overflow-hidden border-r border-sidebar-border">
        <SidebarContents me={me} />
        <button
          type="button"
          onClick={() => setSidebarCollapsed(true)}
          title="Close sidebar (⌘B)"
          className="absolute top-4 right-3 rounded-md p-1.5 text-muted-foreground hover:bg-[#181C22] hover:text-sidebar-foreground"
        >
          <PanelLeftClose className="size-4" />
        </button>
      </div>
    </motion.aside>
  );
}
