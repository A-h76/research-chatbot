import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  PanelLeftClose,
  MessageSquare,
  Library,
  FolderKanban,
  Settings,
  FileText,
  Loader2,
  Home,
  Plus,
  ChevronRight,
  Search,
  Quote,
  StickyNote,
  GitCompare,
  PenLine,
  Upload,
  FileUp,
  Plug,
  Brain,
} from "lucide-react";
import { AccountMenu } from "./AccountMenu";
import { MendeleyIcon, ZoteroIcon } from "./BrandIcons";
import { useUI } from "@/context/UIContext";
import { useFiles, useLibraryStats } from "@/features/files/useFiles";
import { libraryBridgeApi } from "@/features/files/libraryBridgeApi";
import { cn } from "@/lib/utils";
import type { Me } from "@/types/api";

const SIDEBAR_WIDTH = 260;

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-2.5 pb-1 pt-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
      {children}
    </p>
  );
}

function NavItem({
  icon,
  label,
  active,
  onClick,
  muted,
  nested,
  badge,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
  muted?: boolean;
  nested?: boolean;
  badge?: string | number | null;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "relative flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] transition-colors",
        nested && "py-1.5 pl-2",
        active
          ? "bg-sidebar-accent font-medium text-foreground"
          : "text-sidebar-foreground hover:bg-sidebar-accent/80",
        muted && !active && "text-muted-foreground",
      )}
    >
      {active && !nested && (
        <span
          aria-hidden
          className="absolute top-1.5 bottom-1.5 left-0 w-0.5 rounded-full bg-primary"
        />
      )}
      <span
        className={cn(
          "shrink-0",
          active ? "text-primary" : "text-muted-foreground",
        )}
      >
        {icon}
      </span>
      <span className="flex-1 truncate">{label}</span>
      {badge != null && badge !== "" && (
        <span className="rounded-md bg-sidebar-accent px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-muted-foreground">
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
    <div className="flex flex-col gap-0.5 px-1.5">
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
 * Primary workflow nav — mock hierarchy, real Dhund routes only.
 * Solid surfaces (no glass / shimmer). Tokens from design system.
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
  const [libraryOpen, setLibraryOpen] = useState(true);
  const [integrationsOpen, setIntegrationsOpen] = useState(false);
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
  const isResearch = path.startsWith("/research") || path.startsWith("/analysis");
  const isWriting = path.startsWith("/writing");
  const isCitations = path.startsWith("/citations");
  const importProvider = new URLSearchParams(search).get("provider");
  const isImportPanel =
    (path.startsWith("/library") || path.startsWith("/files")) &&
    (hash === "#import" || search.includes("import=1") || Boolean(importProvider));
  const isZoteroImport = isImportPanel && importProvider === "zotero";
  const isMendeleyImport = isImportPanel && importProvider === "mendeley";
  const isUploadImport = isImportPanel && importProvider === "upload";
  const isGlobalChat =
    path.startsWith("/chat") || path.startsWith("/c/");
  const isSettings = path.startsWith("/settings");
  const isIntegrations = isImportPanel;
  const isMoreActive =
    path.startsWith("/search") ||
    path.startsWith("/notes") ||
    path.startsWith("/memory");

  const libraryExpanded = libraryOpen || isLibrary;
  const integrationsExpanded = integrationsOpen || isIntegrations;

  function go(view: Parameters<typeof setActiveView>[0], next: string) {
    setActiveView(view);
    navigate(next);
    setNewOpen(false);
  }

  function goLibraryImport(provider: "zotero" | "mendeley" | "upload" | "bibtex") {
    setLibraryOpen(true);
    if (provider === "zotero" || provider === "mendeley") {
      setIntegrationsOpen(true);
    }
    go("library", `/library?provider=${provider}#import`);
  }

  const zoteroConnected = Boolean(connections?.zotero?.connected);
  const mendeleyConnected = Boolean(connections?.mendeley?.connected);

  return (
    <div className="flex h-full flex-col" onClickCapture={onNavigate}>
      {/* Brand header */}
      <div className="flex items-start gap-2.5 px-3 pt-3.5 pb-1 pr-10">
        <div
          className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground"
          title="Dhund — Research Operating System"
          aria-hidden
        >
          <span className="text-[11px] font-bold leading-none tracking-tight">Dh</span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[15px] font-semibold leading-tight tracking-tight">Dhund</p>
          <p className="truncate text-[11px] text-muted-foreground">Research OS</p>
        </div>
      </div>

      {/* Full-width New CTA */}
      <div className="relative px-3 pt-2 pb-1.5">
        <button
          type="button"
          onClick={() => setNewOpen((o) => !o)}
          className="inline-flex w-full items-center justify-center gap-1.5 rounded-md bg-primary px-3 py-2 text-[13px] font-medium text-primary-foreground hover:opacity-90"
          aria-expanded={newOpen}
          aria-haspopup="menu"
        >
          <Plus className="size-3.5" />
          New
        </button>
        {newOpen && (
          <div
            role="menu"
            className="absolute left-3 right-3 z-20 mt-1 rounded-md border border-border bg-popover py-1 shadow-md"
          >
            <button
              type="button"
              role="menuitem"
              className="flex w-full px-3 py-1.5 text-left text-[13px] hover:bg-muted"
              onClick={() => go("projects", "/projects?new=1")}
            >
              New project
            </button>
            <button
              type="button"
              role="menuitem"
              className="flex w-full px-3 py-1.5 text-left text-[13px] hover:bg-muted"
              onClick={() => go("library", "/library?provider=zotero#import")}
            >
              Import papers
            </button>
            <button
              type="button"
              role="menuitem"
              className="flex w-full px-3 py-1.5 text-left text-[13px] hover:bg-muted"
              onClick={() => go("citations", "/writing")}
            >
              Continue writing
            </button>
            <div className="my-1 border-t border-border" />
            <button
              type="button"
              role="menuitem"
              className="flex w-full px-3 py-1.5 text-left text-[13px] text-muted-foreground hover:bg-muted hover:text-foreground"
              onClick={() => go("chat", "/chat")}
            >
              Ask Dhund…
            </button>
          </div>
        )}
      </div>

      {/* Ask Dhund — solid featured card */}
      <div className="px-3 pb-2 pt-0.5">
        <button
          type="button"
          onClick={() => go("chat", "/chat")}
          className={cn(
            "flex w-full flex-col gap-0.5 rounded-lg bg-accent-soft px-3 py-2.5 text-left transition-colors hover:bg-accent-soft/80",
            isGlobalChat && "ring-1 ring-primary/30",
          )}
        >
          <span className="flex items-center gap-2 text-[13px] font-medium text-foreground">
            <MessageSquare className="size-3.5 text-primary" />
            Ask Dhund
          </span>
          <span className="text-[11px] leading-snug text-muted-foreground">
            Grounded answers from your library
          </span>
        </button>
      </div>

      <div className="scrollbar-thin flex-1 overflow-y-auto">
        {/* Primary */}
        <nav className="space-y-0.5 px-2 pb-1" aria-label="Primary">
          <SectionLabel>Workspace</SectionLabel>
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

          <div>
            <button
              type="button"
              onClick={() => {
                if (!isLibrary) {
                  setLibraryOpen(true);
                  go("library", "/library");
                  return;
                }
                setLibraryOpen((o) => !o);
              }}
              aria-expanded={libraryExpanded}
              className={cn(
                "relative flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] transition-colors",
                isLibrary && !isImportPanel
                  ? "bg-sidebar-accent font-medium text-foreground"
                  : isLibrary
                    ? "font-medium text-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/80",
              )}
            >
              {isLibrary && !isImportPanel && (
                <span
                  aria-hidden
                  className="absolute top-1.5 bottom-1.5 left-0 w-0.5 rounded-full bg-primary"
                />
              )}
              <Library
                className={cn(
                  "size-4 shrink-0",
                  isLibrary ? "text-primary" : "text-muted-foreground",
                )}
              />
              <span className="flex-1 truncate">Library</span>
              {paperCount != null && (
                <span className="rounded-md bg-sidebar-accent px-1.5 py-0.5 text-[10px] font-medium tabular-nums text-muted-foreground">
                  {paperCount}
                </span>
              )}
              <ChevronRight
                className={cn(
                  "size-3.5 text-muted-foreground transition-transform",
                  libraryExpanded && "rotate-90",
                )}
              />
            </button>

            {libraryExpanded && (
              <div className="mt-0.5 space-y-0.5 border-l border-sidebar-border ml-4 pl-1.5">
                <p className="px-2 pb-0.5 pt-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Papers
                </p>
                <NavItem
                  nested
                  icon={<Upload className="size-4" />}
                  label="Upload PDF"
                  active={isUploadImport}
                  onClick={() => goLibraryImport("upload")}
                />
                <NavItem
                  nested
                  icon={<FileUp className="size-4" />}
                  label="BibTeX / RIS"
                  active={isImportPanel && importProvider === "bibtex"}
                  onClick={() => goLibraryImport("bibtex")}
                />
                <NavItem
                  nested
                  muted
                  icon={<Library className="size-4" />}
                  label="All papers"
                  active={isLibrary && !isImportPanel}
                  onClick={() => go("library", "/library")}
                />
              </div>
            )}
          </div>
        </nav>

        {/* Research tools */}
        <nav className="space-y-0.5 px-2 pb-1" aria-label="Research tools">
          <SectionLabel>Research tools</SectionLabel>
          <NavItem
            icon={<GitCompare className="size-4" />}
            label="Research"
            active={isResearch}
            onClick={() => go("library", "/research/compare?tab=matrix")}
          />
          <NavItem
            icon={<PenLine className="size-4" />}
            label="Writing"
            active={isWriting}
            onClick={() => go("citations", "/writing")}
          />
          <NavItem
            icon={<Quote className="size-4" />}
            label="Citations"
            active={isCitations}
            onClick={() => go("citations", "/citations")}
          />
        </nav>

        <div className="mx-3 my-1.5 border-t border-sidebar-border" />

        {/* Recent */}
        <div className="pb-1">
          <SectionLabel>Recent</SectionLabel>
          <RecentPapersList projectId={currentProjectId} />
        </div>

        <div className="mx-3 my-1.5 border-t border-sidebar-border" />

        {/* Integrations */}
        <nav className="space-y-0.5 px-2 pb-1" aria-label="Integrations">
          <div>
            <button
              type="button"
              onClick={() => setIntegrationsOpen((o) => !o)}
              aria-expanded={integrationsExpanded}
              className={cn(
                "relative flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] transition-colors",
                isIntegrations
                  ? "bg-sidebar-accent font-medium text-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/80",
              )}
            >
              {isIntegrations && (
                <span
                  aria-hidden
                  className="absolute top-1.5 bottom-1.5 left-0 w-0.5 rounded-full bg-primary"
                />
              )}
              <Plug
                className={cn(
                  "size-4 shrink-0",
                  isIntegrations ? "text-primary" : "text-muted-foreground",
                )}
              />
              <span className="flex-1 truncate">Integrations</span>
              <span className="flex items-center gap-1">
                <span
                  className={cn(
                    "size-1.5 rounded-full",
                    zoteroConnected ? "bg-emerald-500" : "bg-muted-foreground/40",
                  )}
                  title={zoteroConnected ? "Zotero connected" : "Zotero not connected"}
                />
                <span
                  className={cn(
                    "size-1.5 rounded-full",
                    mendeleyConnected ? "bg-emerald-500" : "bg-muted-foreground/40",
                  )}
                  title={mendeleyConnected ? "Mendeley connected" : "Mendeley not connected"}
                />
              </span>
              <ChevronRight
                className={cn(
                  "size-3.5 text-muted-foreground transition-transform",
                  integrationsExpanded && "rotate-90",
                )}
              />
            </button>
            {integrationsExpanded && (
              <div className="mt-0.5 space-y-0.5 border-l border-sidebar-border ml-4 pl-1.5">
                <button
                  type="button"
                  onClick={() => goLibraryImport("zotero")}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[12px] transition-colors",
                    isZoteroImport
                      ? "bg-sidebar-accent font-medium text-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/80",
                  )}
                >
                  <ZoteroIcon className="size-3.5 shrink-0" />
                  <span className="min-w-0 flex-1 truncate">Zotero</span>
                  <span
                    className={cn(
                      "size-1.5 shrink-0 rounded-full",
                      zoteroConnected ? "bg-emerald-500" : "bg-muted-foreground/40",
                    )}
                    title={zoteroConnected ? "Connected" : "Not connected"}
                    aria-label={zoteroConnected ? "Connected" : "Not connected"}
                  />
                </button>
                <button
                  type="button"
                  onClick={() => goLibraryImport("mendeley")}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[12px] transition-colors",
                    isMendeleyImport
                      ? "bg-sidebar-accent font-medium text-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/80",
                  )}
                >
                  <MendeleyIcon className="size-3.5 shrink-0" />
                  <span className="min-w-0 flex-1 truncate">Mendeley</span>
                  <span
                    className={cn(
                      "size-1.5 shrink-0 rounded-full",
                      mendeleyConnected ? "bg-emerald-500" : "bg-muted-foreground/40",
                    )}
                    title={mendeleyConnected ? "Connected" : "Not connected"}
                    aria-label={mendeleyConnected ? "Connected" : "Not connected"}
                  />
                </button>
              </div>
            )}
          </div>
        </nav>

        {/* More — demoted tools */}
        <div className="px-2 pb-2">
          <button
            type="button"
            onClick={() => setMoreOpen((o) => !o)}
            aria-expanded={moreOpen || isMoreActive}
            className={cn(
              "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px] transition-colors",
              isMoreActive
                ? "bg-sidebar-accent/60 font-medium text-foreground"
                : "text-muted-foreground hover:bg-sidebar-accent/80 hover:text-foreground",
            )}
          >
            <span className="flex-1">More</span>
            <ChevronRight
              className={cn(
                "size-3.5 transition-transform",
                (moreOpen || isMoreActive) && "rotate-90",
              )}
            />
          </button>
          {(moreOpen || isMoreActive) && (
            <div className="mt-0.5 space-y-0.5 pl-1">
              <NavItem
                muted
                icon={<Search className="size-4" />}
                label="Search"
                active={path.startsWith("/search")}
                onClick={() => go("chat", "/search")}
              />
              <NavItem
                muted
                icon={<StickyNote className="size-4" />}
                label="Notes"
                active={path.startsWith("/notes")}
                onClick={() => go("memory", "/notes")}
              />
              <NavItem
                muted
                icon={<Brain className="size-4" />}
                label="Memory"
                active={path.startsWith("/memory")}
                onClick={() => go("memory", "/memory")}
              />
            </div>
          )}
        </div>
      </div>

      {/* Footer: Settings + account */}
      <div className="mt-auto border-t border-sidebar-border px-2 pt-1.5 pb-2">
        <NavItem
          icon={<Settings className="size-4" />}
          label="Settings"
          active={isSettings}
          onClick={() => go("settings", "/settings")}
        />
        <div className="mt-0.5">
          <AccountMenu me={me} />
        </div>
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
      className="relative hidden shrink-0 overflow-hidden border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:block"
    >
      <div className="absolute inset-y-0" style={{ width: SIDEBAR_WIDTH }}>
        <SidebarContents me={me} />
        <button
          type="button"
          onClick={() => setSidebarCollapsed(true)}
          title="Close sidebar (⌘B)"
          className="absolute top-3 right-2 rounded-md p-1.5 text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
        >
          <PanelLeftClose className="size-4" />
        </button>
      </div>
    </motion.aside>
  );
}
