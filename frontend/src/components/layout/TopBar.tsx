import { useEffect } from "react";
import { useLocation, useParams, useNavigate } from "react-router-dom";
import {
  Menu,
  PanelLeftOpen,
  PanelRight,
  ChevronRight,
  Search,
  MessageSquare,
  Bell,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ThemeToggle } from "./ThemeToggle";
import { useUI } from "@/context/UIContext";
import { useFile } from "@/features/files/useFiles";
import { useProjectHub } from "@/features/projects/useProjects";
import { ProjectOverviewPopover } from "@/features/projects/components/ProjectOverviewPopover";
import { isWritingStudioPath } from "@/features/projects/projectWorkspaceNav";
import type { Me } from "@/types/api";

function PaperBreadcrumb() {
  const { fileId } = useParams<{ fileId: string }>();
  const { data: file } = useFile(fileId ? Number(fileId) : null);
  const navigate = useNavigate();
  const { setCurrentProjectId } = useUI();
  const title = file?.title || file?.name || "Paper";
  const parent = file?.project;
  const projectId = parent?.id ?? file?.project_id ?? null;

  useEffect(() => {
    if (projectId != null) setCurrentProjectId(projectId);
  }, [projectId, setCurrentProjectId]);

  return (
    <div className="flex items-center gap-1.5 text-sm">
      {parent || projectId != null ? (
        <button
          type="button"
          onClick={() => {
            if (projectId != null) {
              setCurrentProjectId(projectId);
              navigate(`/projects/${projectId}`);
            }
          }}
          className="max-w-[18ch] truncate text-muted-foreground transition-colors hover:text-foreground"
          title={parent?.name ?? "Project"}
        >
          {parent ? `${parent.emoji} ${parent.name}` : "Project"}
        </button>
      ) : (
        <button
          type="button"
          onClick={() => navigate("/library")}
          className="text-muted-foreground transition-colors hover:text-foreground"
        >
          Library
        </button>
      )}
      <ChevronRight className="size-3.5 text-muted-foreground/50" />
      <span className="max-w-[22ch] truncate font-medium text-foreground" title={title}>
        {title}
      </span>
    </div>
  );
}

function WritingStudioBreadcrumb({ projectId }: { projectId: number }) {
  const navigate = useNavigate();
  const { data: hub } = useProjectHub(projectId);
  const name = hub?.project.name ?? "Project";

  return (
    <div className="flex min-w-0 items-center gap-1 text-[13px]">
      <button
        type="button"
        onClick={() => navigate("/projects")}
        className="shrink-0 text-muted-foreground/80 transition-colors hover:text-foreground"
      >
        Projects
      </button>
      <ChevronRight className="size-3.5 shrink-0 text-muted-foreground/40" />
      <ProjectOverviewPopover projectId={projectId}>
        <span className="truncate">{name}</span>
        <ChevronDown className="size-3.5 shrink-0 text-muted-foreground/70" aria-hidden />
      </ProjectOverviewPopover>
    </div>
  );
}

const STATIC_TITLES: { prefix: string; label: string }[] = [
  { prefix: "/projects", label: "Research" },
  { prefix: "/library", label: "Library" },
  { prefix: "/files", label: "Library" },
  { prefix: "/citations", label: "Citations" },
  { prefix: "/memory", label: "Memory" },
  { prefix: "/notes", label: "Notes" },
  { prefix: "/research", label: "Compare & Gaps" },
  { prefix: "/analysis", label: "Compare & Gaps" },
  { prefix: "/settings", label: "Settings" },
  { prefix: "/admin", label: "Admin" },
  { prefix: "/chat", label: "Ask Dhund" },
  { prefix: "/search", label: "Search" },
  { prefix: "/writing", label: "Writing" },
];

export function TopBar({
  onOpenMobileDrawer,
  me,
}: {
  onOpenMobileDrawer: () => void;
  me?: Me | null;
}) {
  const { sidebarCollapsed, setSidebarCollapsed, rightPanelOpen, setRightPanelOpen, currentProjectId } =
    useUI();
  const location = useLocation();
  const navigate = useNavigate();
  const path = location.pathname;
  const writingStudio =
    currentProjectId != null && isWritingStudioPath(path);

  const isHome = path === "/" || path === "/projects";
  const staticTitle = isHome
    ? "Research"
    : path === "/home"
      ? "Home"
      : path.startsWith("/c/")
        ? "Ask Dhund"
        : STATIC_TITLES.find((t) => path.startsWith(t.prefix))?.label;
  const isPaperPage = path.startsWith("/papers/") && !path.includes("/chat");
  const isPaperChat = path.startsWith("/papers/") && path.includes("/chat");
  const isChat = path.startsWith("/c/") || path.startsWith("/chat") || isPaperChat;

  if (writingStudio && currentProjectId != null) {
    return (
      <header className="writing-studio-topbar flex h-11 shrink-0 items-center gap-4 border-b border-border/60 px-4">
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onOpenMobileDrawer}
          aria-label="Open navigation"
        >
          <Menu className="size-4" aria-hidden />
        </Button>

        <WritingStudioBreadcrumb projectId={currentProjectId} />

        <div className="mx-auto flex min-w-0 max-w-lg flex-1 justify-center px-4">
          <button
            type="button"
            onClick={() => window.dispatchEvent(new CustomEvent("soro:command-palette"))}
            className="flex h-8 w-full max-w-md items-center gap-2 rounded-full border border-border/70 bg-muted/30 px-3.5 text-left text-[12px] text-muted-foreground transition-colors hover:bg-muted/50"
            title="Command palette (⌘K)"
            aria-label="Open command palette"
          >
            <Search className="size-3.5 shrink-0 opacity-70" />
            <span className="min-w-0 flex-1 truncate">Search papers, evidence, notes...</span>
            <kbd className="hidden rounded-md border border-border/60 bg-background/80 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground/80 sm:inline">
              ⌘K
            </kbd>
          </button>
        </div>

        <div className="flex shrink-0 items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-muted-foreground/70"
            title="Notifications"
            aria-label="Notifications"
            disabled
          >
            <Bell className="size-4" />
          </Button>
          {me ? (
            <button
              type="button"
              onClick={() => navigate("/settings")}
              className="rounded-full outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
              title={me.name}
              aria-label="Account"
            >
              <Avatar className="size-7">
                {me.picture && <AvatarImage src={me.picture} alt={me.name} />}
                <AvatarFallback className="text-[11px]">
                  {me.name.slice(0, 1).toUpperCase()}
                </AvatarFallback>
              </Avatar>
            </button>
          ) : (
            <ThemeToggle />
          )}
        </div>
      </header>
    );
  }

  return (
    <header className="flex h-12 shrink-0 items-center gap-1 border-b border-border px-2">
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={onOpenMobileDrawer}
        aria-label="Open navigation"
      >
        <Menu className="size-4" aria-hidden />
      </Button>

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

      {isPaperPage ? (
        <PaperBreadcrumb />
      ) : (
        staticTitle && (
          <h1 className="ml-1 text-[13px] font-medium text-muted-foreground">{staticTitle}</h1>
        )
      )}

      <div className="ml-auto flex items-center gap-1">
        {!isChat && (
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 px-2.5 text-[12px]"
            onClick={() => navigate("/chat")}
            title="Ask Dhund"
          >
            <MessageSquare className="size-3.5 text-primary" />
            <span className="hidden sm:inline">Ask Dhund</span>
          </Button>
        )}
        <Button
          variant="ghost"
          size="sm"
          className="hidden h-8 gap-1.5 px-2 text-muted-foreground md:inline-flex"
          onClick={() => {
            window.dispatchEvent(new CustomEvent("soro:command-palette"));
          }}
          title="Command palette (⌘K)"
          aria-label="Open command palette"
        >
          <Search className="size-3.5" />
          <span className="text-[12px]">Search papers, projects, notes...</span>
          <kbd className="rounded border border-border bg-muted px-1 font-mono text-[10px] text-muted-foreground">
            ⌘K
          </kbd>
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
