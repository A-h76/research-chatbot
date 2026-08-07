/**
 * Calm workspace navigation — Linear/Notion density, not admin chrome.
 */
import { NavLink, useLocation } from "react-router-dom";
import {
  Library,
  FileText,
  Search,
  CheckSquare,
  PenLine,
  FlaskConical,
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
  library: <Library className="size-3.5" strokeWidth={1.75} />,
  papers: <FileText className="size-3.5" strokeWidth={1.75} />,
  research: <Search className="size-3.5" strokeWidth={1.75} />,
  evidence: <CheckSquare className="size-3.5" strokeWidth={1.75} />,
  writing: <PenLine className="size-3.5" strokeWidth={1.75} />,
  review: <FlaskConical className="size-3.5" strokeWidth={1.75} />,
  chat: <MessageSquare className="size-3.5" strokeWidth={1.75} />,
  settings: <Settings className="size-3.5" strokeWidth={1.75} />,
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
      className="writing-studio-nav flex h-full w-[12.5rem] shrink-0 flex-col border-r border-border/60 bg-muted/20"
      data-testid="project-journey-sidebar"
      aria-label="Research workspace"
    >
      <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-2.5 py-5">
        {PROJECT_JOURNEY_NAV.map((item) => {
          const isActive = active === item.id;
          return (
            <NavLink
              key={item.id}
              to={item.href(currentProjectId)}
              className={cn(
                "relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] transition-colors",
                isActive
                  ? "bg-background font-medium text-foreground shadow-sm ring-1 ring-border/50"
                  : "text-muted-foreground/80 hover:bg-background/60 hover:text-foreground",
              )}
            >
              {isActive && (
                <span
                  className="absolute inset-y-2 left-0 w-[2px] rounded-full bg-primary"
                  aria-hidden
                />
              )}
              <span
                className={cn(
                  "shrink-0",
                  isActive ? "text-primary" : "text-muted-foreground/70",
                )}
              >
                {ICONS[item.id]}
              </span>
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      <div className="px-2.5 pb-4 pt-2">
        <NavLink
          to="/settings"
          className={cn(
            "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] transition-colors",
            active === "settings"
              ? "bg-background font-medium text-foreground shadow-sm ring-1 ring-border/50"
              : "text-muted-foreground/70 hover:bg-background/60 hover:text-foreground",
          )}
        >
          <Settings className="size-3.5" strokeWidth={1.75} />
          Settings
        </NavLink>
      </div>
    </aside>
  );
}
