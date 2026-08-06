/**
 * Writing Studio left nav — familiar research-writing destinations.
 * Differentiate via Research Intelligence (right), not novel chrome.
 */
import { NavLink, useLocation } from "react-router-dom";
import {
  Library,
  FileText,
  Search,
  CheckSquare,
  PenLine,
  MessageSquare,
  Settings,
} from "lucide-react";
import { useUI } from "@/context/UIContext";
import {
  PROJECT_JOURNEY_NAV,
  resolveJourneyActive,
  type JourneyNavId,
} from "../projectWorkspaceNav";
import { cn } from "@/lib/utils";

const ICONS: Record<JourneyNavId, React.ReactNode> = {
  library: <Library className="size-4" />,
  papers: <FileText className="size-4" />,
  research: <Search className="size-4" />,
  evidence: <CheckSquare className="size-4" />,
  writing: <PenLine className="size-4" />,
  chat: <MessageSquare className="size-4" />,
  settings: <Settings className="size-4" />,
};

export function ProjectJourneySidebar() {
  const { currentProjectId } = useUI();
  const location = useLocation();

  if (currentProjectId == null) return null;

  const active = resolveJourneyActive(
    location.pathname,
    location.search,
    currentProjectId,
  );

  return (
    <aside
      className="writing-studio-nav flex h-full w-[13.5rem] shrink-0 flex-col border-r border-border bg-background"
      data-testid="project-journey-sidebar"
      aria-label="Research workspace"
    >
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-3">
        {PROJECT_JOURNEY_NAV.map((item) => {
          const isActive = active === item.id;
          return (
            <NavLink
              key={item.id}
              to={item.href(currentProjectId)}
              className={cn(
                "relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] transition-colors",
                isActive
                  ? "bg-primary/10 font-medium text-primary"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
              )}
            >
              {isActive && (
                <span
                  className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-primary"
                  aria-hidden
                />
              )}
              <span className="shrink-0">{ICONS[item.id]}</span>
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      <div className="border-t border-border px-2 py-2">
        <NavLink
          to="/settings"
          className={cn(
            "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] transition-colors",
            active === "settings"
              ? "bg-primary/10 font-medium text-primary"
              : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
          )}
        >
          <Settings className="size-4" />
          Settings
        </NavLink>
      </div>
    </aside>
  );
}
