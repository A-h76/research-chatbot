import { NavLink, useLocation, useParams } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import {
  FileText,
  Brain,
  PenLine,
  MessageSquare,
  Share2,
  StickyNote,
} from "lucide-react";
import { useUI } from "@/context/UIContext";
import { useProjects, useProjectHub } from "../useProjects";
import { cn } from "@/lib/utils";

export type WorkspaceItemId =
  | "papers"
  | "evidence"
  | "writing"
  | "chat"
  | "graph"
  | "notes";

/** Which workspace chip is active for the current route (exclusive). */
export function resolveWorkspaceActive(
  path: string,
  search: string,
  projectId: number,
): WorkspaceItemId | null {
  const params = new URLSearchParams(search);
  const tab = params.get("tab");
  const focus = params.get("focus");

  if (path.startsWith("/writing")) {
    return focus === "evidence" ? "evidence" : "writing";
  }
  if (path.startsWith("/papers/")) {
    if (path.includes("/chat")) return "chat";
    if (tab === "evidence") return "evidence";
    if (tab === "graph") return "graph";
    return "papers";
  }
  if (path.startsWith("/library") || path.startsWith("/files")) return "papers";
  if (path.startsWith("/c/") || path.startsWith("/chat")) return "chat";

  if (path.startsWith(`/projects/${projectId}`)) {
    if (tab === "chat") return "chat";
    if (tab === "notes") return "notes";
    if (tab === "papers") return "papers";
    return null;
  }
  return null;
}

/**
 * Sticky project identity + scoped nav — reminds the user they are inside
 * THIS research project (Sprint 2 Workspace Identity).
 */
export function ProjectWorkspaceBar() {
  const { currentProjectId } = useUI();
  const { data: projects = [] } = useProjects();
  const { data: hub } = useProjectHub(currentProjectId);
  const location = useLocation();
  const { fileId } = useParams<{ fileId?: string }>();
  const path = location.pathname;
  const search = location.search;
  const reduceMotion = useReducedMotion();

  if (currentProjectId == null) return null;
  if (path.startsWith("/settings") || path.startsWith("/admin")) return null;

  const project =
    projects.find((p) => p.id === currentProjectId) ??
    (hub
      ? { id: hub.project.id, name: hub.project.name, emoji: hub.project.emoji }
      : null);
  if (!project) return null;

  const paperCount = hub?.stats.papers;
  const paperGraphHref =
    fileId && path.startsWith("/papers/")
      ? `/papers/${fileId}?tab=graph`
      : `/projects/${currentProjectId}?tab=papers`;

  const active = resolveWorkspaceActive(path, search, currentProjectId);

  const items: {
    id: WorkspaceItemId;
    label: string;
    icon: React.ReactNode;
    to: string;
  }[] = [
    {
      id: "papers",
      label: paperCount != null ? `Papers (${paperCount})` : "Papers",
      icon: <FileText className="size-3.5" />,
      to: `/projects/${currentProjectId}?tab=papers`,
    },
    {
      id: "evidence",
      label: "Evidence",
      icon: <Brain className="size-3.5" />,
      to: "/writing?focus=evidence",
    },
    {
      id: "writing",
      label: "Writing",
      icon: <PenLine className="size-3.5" />,
      to: "/writing",
    },
    {
      id: "chat",
      label: "Chat",
      icon: <MessageSquare className="size-3.5" />,
      to: `/projects/${currentProjectId}?tab=chat`,
    },
    {
      id: "graph",
      label: "Knowledge Graph",
      icon: <Share2 className="size-3.5" />,
      to: paperGraphHref,
    },
    {
      id: "notes",
      label: "Notes",
      icon: <StickyNote className="size-3.5" />,
      to: `/projects/${currentProjectId}?tab=notes`,
    },
  ];

  return (
    <motion.div
      className="flex shrink-0 items-center gap-2 border-b border-border bg-muted/30 px-3 py-1.5"
      data-testid="project-workspace-bar"
      initial={reduceMotion ? false : { opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
    >
      <NavLink
        to={`/projects/${currentProjectId}`}
        className="flex min-w-0 max-w-[22ch] items-center gap-1.5 rounded-md px-1.5 py-1 text-[13px] font-medium text-foreground transition-colors hover:bg-muted"
        title={project.name}
      >
        <span aria-hidden className="shrink-0">
          {project.emoji || "📁"}
        </span>
        <span className="truncate">{project.name}</span>
      </NavLink>

      <span className="hidden h-4 w-px shrink-0 bg-border sm:block" aria-hidden />

      <nav
        className="flex min-w-0 flex-1 items-center gap-0.5 overflow-x-auto scrollbar-none"
        aria-label="Project workspace"
      >
        {items.map((item) => (
          <NavLink
            key={item.id}
            to={item.to}
            className={cn(
              "inline-flex shrink-0 items-center gap-1.5 rounded-md px-2 py-1 text-[12px] transition-colors",
              active === item.id
                ? "bg-background font-medium text-foreground shadow-sm ring-1 ring-border"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {item.icon}
            <span className="hidden sm:inline">{item.label}</span>
            <span className="sm:hidden">{item.label.split(" ")[0]}</span>
          </NavLink>
        ))}
      </nav>
    </motion.div>
  );
}
