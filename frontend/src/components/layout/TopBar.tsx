import { useLocation, useParams, useNavigate } from "react-router-dom";
import { Menu, PanelLeftOpen, PanelRight, ChevronRight, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "./ThemeToggle";
import { useUI } from "@/context/UIContext";
import { useFile } from "@/features/files/useFiles";
import { useProjects } from "@/features/projects/useProjects";
import { cn } from "@/lib/utils";

// Dynamic breadcrumb for /papers/:fileId
function PaperBreadcrumb() {
  const { fileId }    = useParams<{ fileId: string }>();
  const { data: file } = useFile(fileId ? Number(fileId) : null);
  const navigate       = useNavigate();
  const title = file?.title || file?.name || "Paper";

  return (
    <div className="flex items-center gap-1.5 text-sm">
      <button
        onClick={() => navigate("/files")}
        className="text-muted-foreground transition-colors hover:text-foreground"
      >
        Knowledge Library
      </button>
      <ChevronRight className="size-3.5 text-muted-foreground/50" />
      <span className="max-w-[22ch] truncate font-medium text-foreground" title={title}>
        {title}
      </span>
    </div>
  );
}

const STATIC_TITLES: { prefix: string; label: string }[] = [
  { prefix: "/projects",  label: "Research Projects" },
  { prefix: "/files",     label: "Knowledge Library" },
  { prefix: "/citations", label: "Citations" },
  { prefix: "/memory",    label: "Memory" },
  { prefix: "/notes",          label: "Notes" },
  { prefix: "/analysis",         label: "Paper Analysis" },
  { prefix: "/settings",  label: "Settings" },
  { prefix: "/chat",      label: "AI Chat" },
  { prefix: "/search",    label: "Search" },
  { prefix: "/writing",   label: "Writing & Export" },
];

export function TopBar({ onOpenMobileDrawer }: { onOpenMobileDrawer: () => void }) {
  const { sidebarCollapsed, setSidebarCollapsed, rightPanelOpen, setRightPanelOpen, currentProjectId } = useUI();
  const { data: projects = [] } = useProjects();
  const location = useLocation();
  const navigate = useNavigate();
  const path     = location.pathname;

  const staticTitle    = STATIC_TITLES.find((t) => path.startsWith(t.prefix))?.label;
  const isPaperPage    = path.startsWith("/papers/") && !path.includes("/chat");
  const isPaperChat    = path.startsWith("/papers/") && path.includes("/chat");
  const isChat         = path.startsWith("/c/") || isPaperChat;
  const isLibraryScope = path.startsWith("/files") || path.startsWith("/papers/");

  // Active project name shown as a subtle chip when library or chat is scoped
  const activeProject = currentProjectId
    ? projects.find((p) => p.id === currentProjectId)
    : null;

  return (
    <header className="flex h-13 shrink-0 items-center gap-1 border-b border-border/50 px-2">
      {/* Mobile menu */}
      <Button variant="ghost" size="icon" className="md:hidden" onClick={onOpenMobileDrawer}>
        <Menu className="size-4" />
      </Button>

      {/* Expand collapsed sidebar */}
      {sidebarCollapsed && (
        <Button
          variant="ghost"
          size="icon"
          className="hidden md:inline-flex"
          onClick={() => setSidebarCollapsed(false)}
          title="Open sidebar (⌘B)"
        >
          <PanelLeftOpen className="size-4" />
        </Button>
      )}

      {/* Title / breadcrumb */}
      {isPaperPage ? (
        <PaperBreadcrumb />
      ) : (
        staticTitle && (
          <h1 className="ml-1 text-sm font-medium text-muted-foreground">{staticTitle}</h1>
        )
      )}

      {/* Project scope chip */}
      {activeProject && (isLibraryScope || isChat) && (
        <span className={cn(
          "hidden sm:inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground",
          "ml-2",
        )}>
          {activeProject.emoji}
          <span className="max-w-[12ch] truncate">{activeProject.name}</span>
        </span>
      )}

      <div className="ml-auto flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="hidden md:inline-flex"
          onClick={() => navigate("/search")}
          title="Search (S)"
        >
          <Search className="size-4" />
        </Button>
        {isChat && (
          <Button
            variant="ghost"
            size="icon"
            className="hidden lg:inline-flex"
            onClick={() => setRightPanelOpen(!rightPanelOpen)}
            title="Toggle context panel"
          >
            <PanelRight className="size-4" />
          </Button>
        )}
        <ThemeToggle />
      </div>
    </header>
  );
}
