import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  PanelLeftClose,
  MessageSquare,
  Library,
  FolderKanban,
  Settings,
  Loader2,
  Home,
  PlusCircle,
  ChevronDown,
  Search,
  Quote,
  StickyNote,
  PenLine,
  Brain,
  FlaskConical,
} from "lucide-react";
import { AccountMenu } from "./AccountMenu";
import { MendeleyIcon, ZoteroIcon } from "./BrandIcons";
import { useUI } from "@/context/UIContext";
import { useFiles, useLibraryStats } from "@/features/files/useFiles";
import { libraryBridgeApi } from "@/features/files/libraryBridgeApi";
import { isTypingTarget } from "@/lib/keyboard";
import { cn } from "@/lib/utils";
import type { Me, ReadingStatus } from "@/types/api";

const SIDEBAR_WIDTH = 280;
const SIDEBAR_GUTTER = 16;

function readingProgress(status: ReadingStatus | undefined): number {
  if (status === "read") return 100;
  if (status === "reading") return 55;
  return 12;
}

function SectionLabel({
  children,
  onToggle,
  open,
}: {
  children: React.ReactNode;
  onToggle?: () => void;
  open?: boolean;
}) {
  if (onToggle) {
    return (
      <button
        type="button"
        onClick={onToggle}
        className="mb-1.5 flex w-full items-center justify-between px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/80"
      >
        {children}
        <ChevronDown
          className={cn(
            "size-3.5 transition-transform",
            open === false && "-rotate-90",
          )}
        />
      </button>
    );
  }
  return (
    <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/80">
      {children}
    </p>
  );
}

function NavItem({
  icon,
  label,
  active,
  onClick,
  badge,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
  badge?: string | number | null;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group relative flex w-full items-center gap-3 rounded-lg border-l-2 px-3 py-2.5 text-left text-[13px] transition-colors",
        active
          ? "border-primary bg-primary/10 font-semibold text-primary"
          : "border-transparent font-medium text-muted-foreground hover:border-primary/30 hover:bg-sidebar-accent/60 hover:text-primary",
      )}
    >
      <span className="shrink-0">{icon}</span>
      <span className="flex-1 truncate">{label}</span>
      {badge != null && badge !== "" && (
        <span className="rounded bg-sidebar-accent px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-muted-foreground">
          {badge}
        </span>
      )}
    </button>
  );
}

function RecentActivityList({ projectId }: { projectId: number | null }) {
  const navigate = useNavigate();
  const { setActiveView } = useUI();

  const { data: listData, isLoading } = useFiles({
    kind: "document",
    project_id: projectId,
    sort: "recent",
    limit: 5,
  });

  const papers = listData?.items ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1 text-xs text-muted-foreground">
        <Loader2 className="size-3 animate-spin" /> Opening papers…
      </div>
    );
  }

  if (!papers.length) {
    return (
      <p className="px-3 py-1 text-xs text-muted-foreground">No recent papers</p>
    );
  }

  return (
    <div className="space-y-3 px-3">
      {papers.map((paper) => {
        const pct = readingProgress(paper.reading_status);
        return (
          <button
            key={paper.id}
            type="button"
            onClick={() => {
              setActiveView("paper");
              navigate(`/papers/${paper.id}`);
            }}
            className="group w-full cursor-pointer text-left"
          >
            <div className="mb-1 flex items-start justify-between gap-2">
              <span className="truncate text-[13px] text-sidebar-foreground transition-colors group-hover:text-primary">
                {paper.title || paper.name}
              </span>
              <span className="shrink-0 text-[10px] text-muted-foreground">{pct}%</span>
            </div>
            <div className="h-1 w-full overflow-hidden rounded-full bg-sidebar-accent">
              <div
                className="h-full rounded-full bg-primary transition-all group-hover:brightness-110"
                style={{ width: `${pct}%` }}
              />
            </div>
          </button>
        );
      })}
    </div>
  );
}

/**
 * Lab sidebar — mock hierarchy & density, solid surfaces only (no glass / blur / shimmer).
 * Wired to existing Dhund routes and real library / connection data.
 */
export function SidebarContents({
  me,
  onNavigate,
}: {
  me: Me;
  onNavigate?: () => void;
}) {
  const [newOpen, setNewOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(true);
  const { setActiveView, currentProjectId } = useUI();
  const navigate = useNavigate();
  const location = useLocation();
  const path = location.pathname;
  const search = location.search;
  const hash = location.hash;

  const { data: connections } = useQuery({
    queryKey: ["library-connections"],
    queryFn: libraryBridgeApi.connections,
    staleTime: 60_000,
  });

  const { data: libraryStats } = useLibraryStats(currentProjectId);
  const paperCount =
    libraryStats?.total_papers != null && libraryStats.total_papers > 0
      ? libraryStats.total_papers
      : null;

  const isHome = path === "/home";
  const isProjects = path === "/" || path.startsWith("/projects");
  const isLibrary =
    path.startsWith("/library") ||
    path.startsWith("/files") ||
    (path.startsWith("/papers/") && !path.includes("/chat"));
  const isWriting = path.startsWith("/writing");
  const isCitations = path.startsWith("/citations");
  const importProvider = new URLSearchParams(search).get("provider");
  const isImportPanel =
    (path.startsWith("/library") || path.startsWith("/files")) &&
    (hash === "#import" || search.includes("import=1") || Boolean(importProvider));
  const isZoteroImport = isImportPanel && importProvider === "zotero";
  const isMendeleyImport = isImportPanel && importProvider === "mendeley";
  const isGlobalChat = path.startsWith("/chat") || path.startsWith("/c/");
  const isSettings = path.startsWith("/settings");
  const isMoreActive =
    path.startsWith("/search") ||
    path.startsWith("/notes") ||
    path.startsWith("/memory") ||
    path.startsWith("/research") ||
    path.startsWith("/analysis");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target)) return;
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "n") {
        e.preventDefault();
        setNewOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function go(view: Parameters<typeof setActiveView>[0], next: string) {
    setActiveView(view);
    navigate(next);
    setNewOpen(false);
  }

  function goLibraryImport(provider: "zotero" | "mendeley" | "upload" | "bibtex") {
    go("library", `/library?provider=${provider}#import`);
  }

  const zoteroConnected = Boolean(connections?.zotero?.connected);
  const mendeleyConnected = Boolean(connections?.mendeley?.connected);

  return (
    <div className="flex h-full flex-col" onClickCapture={onNavigate}>
      {/* Brand */}
      <div className="flex items-center justify-between gap-2 px-5 pt-5 pb-2 pr-10">
        <div className="flex min-w-0 items-center gap-3">
          <div
            className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground"
            title="Dhund — Research Operating System"
            aria-hidden
          >
            <FlaskConical className="size-5" strokeWidth={2} />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-lg font-semibold tracking-tight text-sidebar-foreground">
              Dhund
            </h1>
            <p className="truncate text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/70">
              Research OS
            </p>
          </div>
        </div>
      </div>

      <nav className="lab-sidebar-scroll flex-1 space-y-5 overflow-y-auto px-3 pb-4">
        {/* New + primary */}
        <div className="space-y-1">
          <div className="relative mb-3">
            <button
              type="button"
              onClick={() => setNewOpen((o) => !o)}
              className="flex w-full items-center justify-between rounded-lg bg-primary px-3 py-2.5 font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-transform hover:scale-[0.98] active:scale-95"
              aria-expanded={newOpen}
              aria-haspopup="menu"
            >
              <span className="flex items-center gap-3 text-[12px] font-semibold uppercase tracking-wide">
                <PlusCircle className="size-5" />
                New Research
              </span>
              <kbd className="rounded bg-primary-foreground/10 px-1.5 py-0.5 text-[10px] opacity-70">
                ⌘N
              </kbd>
            </button>
            {newOpen && (
              <div
                role="menu"
                className="absolute left-0 right-0 z-20 mt-1 rounded-lg border border-sidebar-border bg-sidebar-accent py-1 shadow-xl"
              >
                <button
                  type="button"
                  role="menuitem"
                  className="flex w-full px-3 py-2 text-left text-[13px] text-sidebar-foreground hover:bg-sidebar/40"
                  onClick={() => go("projects", "/projects?new=1")}
                >
                  New project
                </button>
                <button
                  type="button"
                  role="menuitem"
                  className="flex w-full px-3 py-2 text-left text-[13px] text-sidebar-foreground hover:bg-sidebar/40"
                  onClick={() => goLibraryImport("upload")}
                >
                  Import papers
                </button>
                <button
                  type="button"
                  role="menuitem"
                  className="flex w-full px-3 py-2 text-left text-[13px] text-sidebar-foreground hover:bg-sidebar/40"
                  onClick={() => go("citations", "/writing")}
                >
                  Continue writing
                </button>
                <div className="my-1 border-t border-sidebar-border" />
                <button
                  type="button"
                  role="menuitem"
                  className="flex w-full px-3 py-2 text-left text-[13px] text-muted-foreground hover:bg-sidebar/40 hover:text-sidebar-foreground"
                  onClick={() => go("chat", "/chat")}
                >
                  Ask Dhund…
                </button>
              </div>
            )}
          </div>

          <NavItem
            icon={<Home className="size-5" />}
            label="Home"
            active={isHome}
            onClick={() => go("library", "/home")}
          />
          <NavItem
            icon={<FolderKanban className="size-5" />}
            label="Projects"
            active={isProjects}
            onClick={() => go("projects", "/")}
          />
          <NavItem
            icon={<Library className="size-5" />}
            label="Library"
            active={isLibrary && !isImportPanel}
            badge={paperCount}
            onClick={() => go("library", "/library")}
          />
        </div>

        {/* Ask Dhund — solid primary card (no glass / shimmer) */}
        <div className="px-1">
          <button
            type="button"
            onClick={() => go("chat", "/chat")}
            className={cn(
              "w-full cursor-pointer rounded-xl bg-primary p-4 text-left text-primary-foreground shadow-md shadow-primary/15 transition-shadow hover:shadow-lg hover:shadow-primary/25",
              isGlobalChat && "ring-1 ring-primary-foreground/30",
            )}
          >
            <div className="mb-1.5 flex items-center gap-3">
              <MessageSquare className="size-5 fill-current" />
              <h3 className="text-[15px] font-bold">Ask Dhund</h3>
            </div>
            <p className="text-[11px] leading-relaxed text-primary-foreground/80">
              Grounded answers from your library.
            </p>
          </button>
        </div>

        {/* Research tools */}
        <div>
          <SectionLabel open={toolsOpen} onToggle={() => setToolsOpen((o) => !o)}>
            Research Tools
          </SectionLabel>
          {toolsOpen && (
            <div className="space-y-0.5">
              <NavItem
                icon={<Quote className="size-5" />}
                label="Citations"
                active={isCitations}
                onClick={() => go("citations", "/citations")}
              />
              <NavItem
                icon={<Library className="size-5" />}
                label="Papers"
                active={isLibrary && !isImportPanel}
                onClick={() => go("library", "/library")}
              />
              <NavItem
                icon={<PenLine className="size-5" />}
                label="Writing Tools"
                active={isWriting}
                onClick={() => go("citations", "/writing")}
              />
            </div>
          )}
        </div>

        {/* Recent — real reading_status progress, no fake % */}
        <div>
          <SectionLabel>Recent Activity</SectionLabel>
          <RecentActivityList projectId={currentProjectId} />
        </div>

        {/* Integrations — flat list like mock */}
        <div>
          <SectionLabel>Integrations</SectionLabel>
          <div className="space-y-0.5">
            <button
              type="button"
              onClick={() => goLibraryImport("zotero")}
              className={cn(
                "flex w-full items-center gap-3 px-3 py-2 text-left text-[14px] transition-colors",
                isZoteroImport
                  ? "text-primary"
                  : "text-muted-foreground hover:text-primary",
              )}
            >
              <span
                className={cn(
                  "size-2 shrink-0 rounded-full",
                  zoteroConnected ? "bg-emerald-500" : "bg-muted-foreground/40",
                )}
                aria-hidden
              />
              <ZoteroIcon className="size-3.5 shrink-0 opacity-80" />
              <span className="truncate">Zotero Cloud</span>
            </button>
            <button
              type="button"
              onClick={() => goLibraryImport("mendeley")}
              className={cn(
                "flex w-full items-center gap-3 px-3 py-2 text-left text-[14px] transition-colors",
                isMendeleyImport
                  ? "text-primary"
                  : "text-muted-foreground hover:text-primary",
              )}
            >
              <span
                className={cn(
                  "size-2 shrink-0 rounded-full",
                  mendeleyConnected ? "bg-emerald-500" : "bg-muted-foreground/40",
                )}
                aria-hidden
              />
              <MendeleyIcon className="size-3.5 shrink-0 opacity-80" />
              <span className="truncate">Mendeley Library</span>
            </button>
          </div>
        </div>

        {/* More — demoted Dhund tools */}
        <div>
          <button
            type="button"
            onClick={() => setMoreOpen((o) => !o)}
            aria-expanded={moreOpen || isMoreActive}
            className="mb-1 flex w-full items-center justify-between px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/80"
          >
            More
            <ChevronDown
              className={cn(
                "size-3.5 transition-transform",
                !(moreOpen || isMoreActive) && "-rotate-90",
              )}
            />
          </button>
          {(moreOpen || isMoreActive) && (
            <div className="space-y-0.5">
              <NavItem
                icon={<Search className="size-5" />}
                label="Search"
                active={path.startsWith("/search")}
                onClick={() => go("chat", "/search")}
              />
              <NavItem
                icon={<StickyNote className="size-5" />}
                label="Notes"
                active={path.startsWith("/notes")}
                onClick={() => go("memory", "/notes")}
              />
              <NavItem
                icon={<Brain className="size-5" />}
                label="Memory"
                active={path.startsWith("/memory")}
                onClick={() => go("memory", "/memory")}
              />
              <NavItem
                icon={<FlaskConical className="size-5" />}
                label="Research Compare"
                active={path.startsWith("/research") || path.startsWith("/analysis")}
                onClick={() => go("library", "/research/compare?tab=matrix")}
              />
            </div>
          )}
        </div>
      </nav>

      {/* Footer */}
      <div className="space-y-1 border-t border-sidebar-border/80 p-4">
        <button
          type="button"
          onClick={() => go("settings", "/settings")}
          className={cn(
            "group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-[14px] transition-colors",
            isSettings
              ? "bg-sidebar-accent text-sidebar-foreground"
              : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
          )}
        >
          <Settings className="size-5 transition-transform group-hover:rotate-45" />
          Settings
        </button>
        <div className="mt-2 rounded-xl border border-sidebar-border/60 bg-sidebar-accent/40 px-1 py-1 shadow-sm">
          <AccountMenu me={me} />
        </div>
      </div>
    </div>
  );
}

export function Sidebar({ me }: { me: Me }) {
  const { sidebarCollapsed, setSidebarCollapsed } = useUI();
  const openWidth = SIDEBAR_WIDTH + SIDEBAR_GUTTER;

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarCollapsed ? 0 : openWidth }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="relative hidden shrink-0 overflow-hidden md:block"
    >
      <div
        className="absolute inset-y-0 left-0 py-4 pl-4"
        style={{ width: openWidth }}
      >
        <div className="dhund-lab-sidebar relative flex h-full w-[280px] flex-col overflow-hidden rounded-xl border border-sidebar-border shadow-2xl">
          <SidebarContents me={me} />
          <button
            type="button"
            onClick={() => setSidebarCollapsed(true)}
            title="Close sidebar (⌘B)"
            className="absolute top-4 right-3 rounded-md p-1.5 text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
          >
            <PanelLeftClose className="size-4" />
          </button>
        </div>
      </div>
    </motion.aside>
  );
}
