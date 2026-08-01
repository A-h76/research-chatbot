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
  Plug,
  FileText,
} from "lucide-react";
import { AccountMenu } from "./AccountMenu";
import { MendeleyIcon, ZoteroIcon } from "./BrandIcons";
import { useUI } from "@/context/UIContext";
import { useFiles, useLibraryStats } from "@/features/files/useFiles";
import { libraryBridgeApi } from "@/features/files/libraryBridgeApi";
import { isTypingTarget } from "@/lib/keyboard";
import { cn } from "@/lib/utils";
import type { Me } from "@/types/api";

const SIDEBAR_WIDTH = 280;

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
        "group relative flex w-full items-center gap-3 rounded-lg border-l-2 px-3 py-2 text-left text-[13px] transition-colors",
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

function RecentPapersList({ projectId }: { projectId: number | null }) {
  const navigate = useNavigate();
  const { setActiveView } = useUI();

  const { data: listData, isLoading } = useFiles({
    kind: "document",
    project_id: projectId,
    sort: "recent",
    limit: 4,
  });

  const papers = listData?.items ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1 text-xs text-muted-foreground">
        <Loader2 className="size-3 animate-spin" /> …
      </div>
    );
  }

  if (!papers.length) return null;

  return (
    <div className="flex flex-col gap-0.5 px-1">
      {papers.map((paper) => (
        <button
          key={paper.id}
          type="button"
          onClick={() => {
            setActiveView("paper");
            navigate(`/papers/${paper.id}`);
          }}
          className="flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs text-sidebar-foreground hover:bg-sidebar-accent"
        >
          <FileText className="size-3 shrink-0 text-muted-foreground" />
          <span className="min-w-0 flex-1 truncate">
            {paper.title || paper.name}
          </span>
        </button>
      ))}
    </div>
  );
}

/**
 * Simplified lab sidebar — primary destinations only.
 * Features (Citations, Compare, Integrations) live under More.
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
    path.startsWith("/citations") ||
    path.startsWith("/notes") ||
    path.startsWith("/memory") ||
    path.startsWith("/research") ||
    path.startsWith("/analysis") ||
    isImportPanel;

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
      <div className="flex items-center justify-between gap-2 px-5 pt-5 pb-2 pr-10">
        <div className="flex min-w-0 items-center gap-3">
          <div
            className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground"
            title="Dhund — Research Operating System"
            aria-hidden
          >
            <span className="text-[11px] font-bold tracking-tight">Dh</span>
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-[15px] font-semibold tracking-tight text-sidebar-foreground">
              Dhund
            </h1>
            <p className="truncate text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/70">
              Research OS
            </p>
          </div>
        </div>
      </div>

      <nav className="lab-sidebar-scroll flex-1 space-y-4 overflow-y-auto px-3 pb-4">
        <div className="relative">
          <button
            type="button"
            onClick={() => setNewOpen((o) => !o)}
            className="flex w-full items-center justify-between rounded-lg border border-sidebar-border bg-sidebar-accent/40 px-3 py-2.5 text-sidebar-foreground transition-colors hover:bg-sidebar-accent"
            aria-expanded={newOpen}
            aria-haspopup="menu"
          >
            <span className="flex items-center gap-2.5 text-[12px] font-semibold tracking-wide">
              <PlusCircle className="size-4 text-primary" />
              New
            </span>
            <kbd className="rounded bg-sidebar/50 px-1.5 py-0.5 text-[10px] text-muted-foreground">
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
            </div>
          )}
        </div>

        {/* Primary destinations */}
        <div className="space-y-0.5">
          <NavItem
            icon={<Home className="size-4" />}
            label="Home"
            active={isHome}
            onClick={() => go("library", "/home")}
          />
          <NavItem
            icon={<FolderKanban className="size-4" />}
            label="Projects"
            active={isProjects}
            onClick={() => go("projects", "/")}
          />
          <NavItem
            icon={<Library className="size-4" />}
            label="Library"
            active={isLibrary && !isImportPanel}
            badge={paperCount}
            onClick={() => go("library", "/library")}
          />
          <NavItem
            icon={<PenLine className="size-4" />}
            label="Writing"
            active={isWriting}
            onClick={() => go("citations", "/writing")}
          />
        </div>

        <div className="mx-1 border-t border-sidebar-border/80" />

        {/* Ask Dhund — secondary, not competing with nav accent */}
        <button
          type="button"
          onClick={() => go("chat", "/chat")}
          className={cn(
            "w-full rounded-lg border border-sidebar-border bg-transparent px-3 py-2.5 text-left transition-colors hover:bg-sidebar-accent/60",
            isGlobalChat && "border-primary/40 bg-primary/10",
          )}
        >
          <span className="flex items-center gap-2 text-[13px] font-semibold text-sidebar-foreground">
            <MessageSquare className="size-4 text-primary" />
            Ask Dhund
          </span>
        </button>

        <div className="mx-1 border-t border-sidebar-border/80" />

        {/* Recent — titles only */}
        <div>
          <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/80">
            Recent
          </p>
          <RecentPapersList projectId={currentProjectId} />
        </div>

        {/* More — demoted features */}
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
                icon={<Quote className="size-4" />}
                label="Citations"
                active={path.startsWith("/citations")}
                onClick={() => go("citations", "/citations")}
              />
              <NavItem
                icon={<FlaskConical className="size-4" />}
                label="Research"
                active={path.startsWith("/research") || path.startsWith("/analysis")}
                onClick={() => go("library", "/research/compare?tab=matrix")}
              />
              <NavItem
                icon={<Search className="size-4" />}
                label="Search"
                active={path.startsWith("/search")}
                onClick={() => go("chat", "/search")}
              />
              <NavItem
                icon={<StickyNote className="size-4" />}
                label="Notes"
                active={path.startsWith("/notes")}
                onClick={() => go("memory", "/notes")}
              />
              <NavItem
                icon={<Brain className="size-4" />}
                label="Memory"
                active={path.startsWith("/memory")}
                onClick={() => go("memory", "/memory")}
              />
              <NavItem
                icon={<Plug className="size-4" />}
                label="Integrations"
                active={isImportPanel}
                onClick={() => goLibraryImport("upload")}
              />
              <div className="ml-2 space-y-0.5 border-l border-sidebar-border pl-2">
                  <button
                    type="button"
                    onClick={() => goLibraryImport("zotero")}
                    className={cn(
                      "flex w-full items-center gap-2 px-2 py-1.5 text-left text-[12px]",
                      isZoteroImport
                        ? "text-primary"
                        : "text-muted-foreground hover:text-primary",
                    )}
                  >
                    <span
                      className={cn(
                        "size-1.5 rounded-full",
                        zoteroConnected ? "bg-emerald-500" : "bg-muted-foreground/40",
                      )}
                    />
                    <ZoteroIcon className="size-3" />
                    Zotero
                  </button>
                  <button
                    type="button"
                    onClick={() => goLibraryImport("mendeley")}
                    className={cn(
                      "flex w-full items-center gap-2 px-2 py-1.5 text-left text-[12px]",
                      isMendeleyImport
                        ? "text-primary"
                        : "text-muted-foreground hover:text-primary",
                    )}
                  >
                    <span
                      className={cn(
                        "size-1.5 rounded-full",
                        mendeleyConnected ? "bg-emerald-500" : "bg-muted-foreground/40",
                      )}
                    />
                    <MendeleyIcon className="size-3" />
                    Mendeley
                  </button>
                </div>
            </div>
          )}
        </div>
      </nav>

      <div className="space-y-1 border-t border-sidebar-border/80 p-3">
        <button
          type="button"
          onClick={() => go("settings", "/settings")}
          className={cn(
            "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-[13px] transition-colors",
            isSettings
              ? "bg-sidebar-accent text-sidebar-foreground"
              : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
          )}
        >
          <Settings className="size-4" />
          Settings
        </button>
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
      <div
        className="dhund-lab-sidebar absolute inset-y-0 left-0 flex w-[280px] flex-col overflow-hidden border-r border-sidebar-border"
      >
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
    </motion.aside>
  );
}
