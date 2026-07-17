import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  PanelLeftClose, Search, MessageSquare, Library,
  FolderKanban, Quote, Brain, Settings, FileText,
  ChevronRight, Loader2, LayoutDashboard, StickyNote, GitCompare, Wand2,
} from "lucide-react";
import { NewChatButton } from "./NewChatButton";
import { ConversationList } from "./ConversationList";
import { AccountMenu } from "./AccountMenu";
import { useUI } from "@/context/UIContext";
import { useProjects } from "@/features/projects/useProjects";
import { useFiles } from "@/features/files/useFiles";
import { cn } from "@/lib/utils";
import type { Me } from "@/types/api";

// ── Shared nav item ────────────────────────────────────────────────────────
function NavItem({
  icon,
  label,
  active,
  badge,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  badge?: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-sm transition-colors",
        active
          ? "bg-sidebar-accent font-medium text-foreground"
          : "text-sidebar-foreground hover:bg-sidebar-accent",
      )}
    >
      <span className={cn("shrink-0", active ? "text-primary" : "text-muted-foreground")}>
        {icon}
      </span>
      <span className="flex-1 truncate">{label}</span>
      {badge !== undefined && badge > 0 && (
        <span className={cn(
          "rounded-full px-1.5 py-0.5 text-[10px] font-semibold tabular-nums",
          active ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground",
        )}>
          {badge}
        </span>
      )}
    </button>
  );
}

// ── Recent papers mini-list under Library nav ──────────────────────────────
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
      <div className="flex items-center gap-2 px-4 py-1 text-xs text-muted-foreground">
        <Loader2 className="size-3 animate-spin" /> Loading…
      </div>
    );
  }

  if (!papers.length) return null;

  return (
    <div className="flex flex-col gap-0.5 pl-6 pr-2">
      {papers.map((paper) => (
        <button
          key={paper.id}
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

// ── Project list with paper counts ─────────────────────────────────────────
function ProjectNav() {
  const { data: projects = [] } = useProjects();
  const { currentProjectId, setCurrentProjectId, setActiveView } = useUI();
  const navigate = useNavigate();

  if (!projects.length) return null;

  return (
    <div className="mt-1">
      <div className="flex items-center justify-between px-3 pb-1">
        <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Projects
        </span>
        <button
          onClick={() => { setActiveView("projects"); navigate("/projects"); }}
          className="rounded-md p-1 text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
          title="Manage projects"
        >
          <Settings className="size-3" />
        </button>
      </div>
      <div className="flex flex-col gap-0.5 px-2">
        {projects.map((p) => (
          <button
            key={p.id}
            onClick={() => {
              setCurrentProjectId(currentProjectId === p.id ? null : p.id);
              setActiveView("chat");
              navigate("/");
            }}
            className={cn(
              "flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-sm transition-colors",
              currentProjectId === p.id
                ? "bg-sidebar-accent font-medium text-foreground"
                : "text-sidebar-foreground hover:bg-sidebar-accent",
            )}
          >
            <span className="text-base leading-none">{p.emoji}</span>
            <span className="min-w-0 flex-1 truncate">{p.name}</span>
            <ChevronRight className={cn(
              "size-3 shrink-0 text-muted-foreground transition-transform",
              currentProjectId === p.id && "rotate-90",
            )} />
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Main sidebar contents ──────────────────────────────────────────────────
export function SidebarContents({ me, onNavigate }: { me: Me; onNavigate?: () => void }) {
  const [search, setSearch] = useState("");
  const [libraryExpanded, setLibraryExpanded] = useState(false);
  const { activeView, setActiveView, currentProjectId } = useUI();
  const navigate = useNavigate();
  const location = useLocation();

  // Keep activeView in sync with the URL
  const path = location.pathname;
  const derivedView: typeof activeView =
    path.startsWith("/papers/") ? "paper"
    : path.startsWith("/files") ? "library"
    : path.startsWith("/projects") ? "projects"
    : path.startsWith("/citations") ? "citations"
    : path.startsWith("/analysis") ? "library"
    : path.startsWith("/search")   ? "chat"
    : path.startsWith("/writing")  ? "citations"
    : path.startsWith("/notes")    ? "memory"
    : path.startsWith("/memory")   ? "memory"
    : path.startsWith("/settings") ? "settings"
    : "chat";

  const isLibraryActive = derivedView === "library" || derivedView === "paper";

  // Auto-expand on entering the library section; afterwards the toggle
  // below fully controls it (isLibraryActive stays true while browsing
  // /files, so it can't be part of the display condition or it would
  // never let the user collapse the list on that page).
  useEffect(() => {
    if (isLibraryActive) setLibraryExpanded(true);
  }, [isLibraryActive]);

  function go(view: typeof activeView, path: string) {
    setActiveView(view);
    navigate(path);
  }

  return (
    <div className="flex h-full flex-col" onClickCapture={onNavigate}>
      {/* Brand */}
      <div className="flex items-center gap-2 px-3 pt-3 pb-2">
        <div className="flex size-7 items-center justify-center rounded-full bg-foreground text-sm text-background">
          ✦
        </div>
        <span className="text-sm font-semibold">Soro</span>
      </div>

      {/* New chat */}
      <div className="px-2 pb-1">
        <NewChatButton />
      </div>

      {/* Primary nav */}
      <div className="px-2 pb-1 space-y-0.5">
        <NavItem
          icon={<LayoutDashboard className="size-4" />}
          label="Dashboard"
          active={derivedView === "chat" && path === "/"}
          onClick={() => go("chat", "/")}
        />
        <NavItem
          icon={<MessageSquare className="size-4" />}
          label="AI Chat"
          active={derivedView === "chat" && path !== "/" && !path.startsWith("/search")}
          onClick={() => go("chat", "/chat")}
        />
        <NavItem
          icon={<Search className="size-4" />}
          label="Search"
          active={path.startsWith("/search")}
          onClick={() => go("chat", "/search")}
        />

        {/* Library with expandable recent papers */}
        <div>
          <button
            onClick={() => {
              setLibraryExpanded((e) => !e);
              go("library", "/files");
            }}
            className={cn(
              "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-sm transition-colors",
              isLibraryActive
                ? "bg-sidebar-accent font-medium text-foreground"
                : "text-sidebar-foreground hover:bg-sidebar-accent",
            )}
          >
            <Library className={cn(
              "size-4 shrink-0",
              isLibraryActive ? "text-primary" : "text-muted-foreground",
            )} />
            <span className="flex-1">Knowledge Library</span>
            <ChevronRight className={cn(
              "size-3 text-muted-foreground transition-transform duration-150",
              libraryExpanded && "rotate-90",
            )} />
          </button>

          {/* Recent papers accordion */}
          {libraryExpanded && (
            <div className="mt-0.5 mb-1 max-h-40 overflow-y-auto scrollbar-thin">
              <RecentPapersList projectId={currentProjectId} />
            </div>
          )}
        </div>

        <NavItem
          icon={<GitCompare className="size-4" />}
          label="Paper Analysis"
          active={path.startsWith("/analysis")}
          onClick={() => go("library", "/analysis/compare")}
        />
        <NavItem
          icon={<FolderKanban className="size-4" />}
          label="Projects"
          active={derivedView === "projects"}
          onClick={() => go("projects", "/projects")}
        />
        <NavItem
          icon={<Quote className="size-4" />}
          label="Citations"
          active={derivedView === "citations" && !path.startsWith("/writing")}
          onClick={() => go("citations", "/citations")}
        />
        <NavItem
          icon={<Wand2 className="size-4" />}
          label="Writing & Export"
          active={path.startsWith("/writing")}
          onClick={() => go("citations", "/writing")}
        />
        <NavItem
          icon={<StickyNote className="size-4" />}
          label="Notes"
          active={derivedView === "memory" && path.startsWith("/notes")}
          onClick={() => go("memory", "/notes")}
        />
        <NavItem
          icon={<Brain className="size-4" />}
          label="Memory"
          active={derivedView === "memory" && !path.startsWith("/notes")}
          onClick={() => go("memory", "/memory")}
        />
      </div>

      {/* Divider */}
      <div className="mx-3 my-1 border-t border-sidebar-border" />

      {/* Projects quick-switcher */}
      <div className="pb-1">
        <ProjectNav />
      </div>

      {/* Divider */}
      <div className="mx-3 my-1 border-t border-sidebar-border" />

      {/* Chat search + list */}
      <div className="mx-3 mb-2 flex items-center gap-2 rounded-lg border border-sidebar-border bg-background/40 px-2.5 py-1.5">
        <Search className="size-3.5 shrink-0 text-muted-foreground" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search chats"
          className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />
      </div>
      <div className="scrollbar-thin flex-1 overflow-y-auto pb-2">
        <p className="px-4 pb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Recent chats
        </p>
        <ConversationList search={search} />
      </div>

      {/* Account */}
      <div className="border-t border-sidebar-border p-2">
        <NavItem
          icon={<Settings className="size-4" />}
          label="Settings"
          active={derivedView === "settings"}
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
      animate={{ width: sidebarCollapsed ? 0 : 272 }}
      transition={{ duration: 0.22, ease: "easeInOut" }}
      className="relative hidden shrink-0 overflow-hidden border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:block"
    >
      <div className="absolute inset-y-0 w-[272px]">
        <SidebarContents me={me} />
        <button
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
