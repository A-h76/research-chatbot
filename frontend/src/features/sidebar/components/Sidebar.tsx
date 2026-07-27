import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
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
  Wand2,
  Plus,
  ChevronRight,
  Search,
  Quote,
  StickyNote,
  GitCompare,
} from "lucide-react";
import { AccountMenu } from "./AccountMenu";
import { useUI } from "@/context/UIContext";
import { useFiles } from "@/features/files/useFiles";
import { cn } from "@/lib/utils";
import type { Me } from "@/types/api";

function NavItem({
  icon,
  label,
  active,
  onClick,
  muted,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
  muted?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-[13px] transition-colors",
        active
          ? "bg-sidebar-accent font-medium text-foreground"
          : "text-sidebar-foreground hover:bg-sidebar-accent/80",
        muted && !active && "text-muted-foreground",
      )}
    >
      <span
        className={cn(
          "shrink-0",
          active ? "text-foreground" : "text-muted-foreground",
        )}
      >
        {icon}
      </span>
      <span className="flex-1 truncate">{label}</span>
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
        <Loader2 className="size-3 animate-spin" /> Loading…
      </div>
    );
  }

  if (!papers.length) return null;

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
          className="flex items-center gap-2 rounded-md px-2 py-1 text-left text-xs text-sidebar-foreground hover:bg-sidebar-accent"
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
 * D6 — Primary: Home · Library · Projects · Writing.
 * Global Chat demoted under More (routes kept).
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

  const isHome = path === "/";
  const isLibrary =
    path.startsWith("/library") ||
    path.startsWith("/files") ||
    (path.startsWith("/papers/") && !path.includes("/chat"));
  const isProjects = path.startsWith("/projects");
  const isWriting = path.startsWith("/writing");
  const isGlobalChat =
    path.startsWith("/chat") || path.startsWith("/c/");
  const isPaperChat = path.startsWith("/papers/") && path.includes("/chat");
  const isSettings = path.startsWith("/settings");
  const isMoreActive =
    isGlobalChat ||
    path.startsWith("/search") ||
    path.startsWith("/research") ||
    path.startsWith("/analysis") ||
    path.startsWith("/citations") ||
    path.startsWith("/notes") ||
    path.startsWith("/memory");

  function go(view: Parameters<typeof setActiveView>[0], next: string) {
    setActiveView(view);
    navigate(next);
    setNewOpen(false);
  }

  return (
    <div className="flex h-full flex-col" onClickCapture={onNavigate}>
      <div className="flex items-center gap-2 px-3 pt-3 pb-2">
        <div className="flex size-6 items-center justify-center rounded-md bg-primary text-[11px] font-semibold text-primary-foreground">
          S
        </div>
        <span className="text-[15px] font-semibold tracking-tight">Soro</span>
        <div className="relative ml-auto">
          <button
            type="button"
            onClick={() => setNewOpen((o) => !o)}
            className="inline-flex items-center gap-1 rounded-md bg-primary px-2 py-1 text-[12px] font-medium text-primary-foreground hover:opacity-90"
            aria-expanded={newOpen}
            aria-haspopup="menu"
          >
            <Plus className="size-3.5" />
            New
          </button>
          {newOpen && (
            <div
              role="menu"
              className="absolute right-0 z-20 mt-1 w-44 rounded-md border border-border bg-popover py-1 shadow-md"
            >
              <button
                type="button"
                role="menuitem"
                className="flex w-full px-3 py-1.5 text-left text-[13px] hover:bg-muted"
                onClick={() => go("library", "/library")}
              >
                Upload paper
              </button>
              <button
                type="button"
                role="menuitem"
                className="flex w-full px-3 py-1.5 text-left text-[13px] hover:bg-muted"
                onClick={() => go("projects", "/projects")}
              >
                New project
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
                Ask Soro…
              </button>
            </div>
          )}
        </div>
      </div>

      <nav className="space-y-0.5 px-2 pb-1" aria-label="Primary">
        <NavItem
          icon={<Home className="size-4" />}
          label="Home"
          active={isHome}
          onClick={() => go("library", "/")}
        />
        <NavItem
          icon={<Library className="size-4" />}
          label="Library"
          active={isLibrary}
          onClick={() => go("library", "/library")}
        />
        <NavItem
          icon={<FolderKanban className="size-4" />}
          label="Projects"
          active={isProjects}
          onClick={() => go("projects", "/projects")}
        />
        <NavItem
          icon={<Wand2 className="size-4" />}
          label="Writing"
          active={isWriting}
          onClick={() => go("citations", "/writing")}
        />
      </nav>

      {/* D6 — demoted tools + global chat */}
      <div className="px-2 pb-2">
        <button
          type="button"
          onClick={() => setMoreOpen((o) => !o)}
          aria-expanded={moreOpen || isMoreActive}
          className={cn(
            "flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-[13px] transition-colors",
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
              icon={<GitCompare className="size-4" />}
              label="Compare"
              active={path.startsWith("/research") || path.startsWith("/analysis")}
              onClick={() => go("library", "/research/compare")}
            />
            <NavItem
              muted
              icon={<Quote className="size-4" />}
              label="Citations"
              active={path.startsWith("/citations")}
              onClick={() => go("citations", "/citations")}
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
              icon={<MessageSquare className="size-4" />}
              label="Ask Soro"
              active={isGlobalChat && !isPaperChat}
              onClick={() => go("chat", "/chat")}
            />
          </div>
        )}
      </div>

      <div className="mx-3 border-t border-sidebar-border" />

      <div className="scrollbar-thin flex-1 overflow-y-auto py-2">
        <p className="px-3 pb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Recent papers
        </p>
        <RecentPapersList projectId={currentProjectId} />
      </div>

      <div className="border-t border-sidebar-border p-2">
        <NavItem
          icon={<Settings className="size-4" />}
          label="Settings"
          active={isSettings}
          onClick={() => go("settings", "/settings")}
        />
        <div className="mt-1">
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
      animate={{ width: sidebarCollapsed ? 0 : 240 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="relative hidden shrink-0 overflow-hidden border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:block"
    >
      <div className="absolute inset-y-0 w-[240px]">
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
