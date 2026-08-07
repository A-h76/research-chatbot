/**
 * Project-scoped journey nav — dedicated research environment, not a SaaS dashboard.
 * Inspired by Linear / Arc / Anara: narrow, muted, location-like active state.
 */
import { NavLink, useLocation } from "react-router-dom";
import {
  FileText,
  Search,
  BookMarked,
  PenLine,
  FlaskConical,
  MessageSquare,
  Settings,
} from "lucide-react";
import { useUI } from "@/context/UIContext";
import {
  PROJECT_JOURNEY_SECONDARY,
  PROJECT_JOURNEY_WORKFLOW,
  resolveJourneyActive,
  type JourneyNavId,
  type JourneyNavItem,
} from "../projectWorkspaceNav";
import { cn } from "@/lib/utils";

const ICONS: Partial<Record<JourneyNavId, React.ReactNode>> = {
  papers: <FileText className="size-4" strokeWidth={1.5} />,
  research: <Search className="size-4" strokeWidth={1.5} />,
  evidence: <BookMarked className="size-4" strokeWidth={1.5} />,
  writing: <PenLine className="size-4" strokeWidth={1.5} />,
  review: <FlaskConical className="size-4" strokeWidth={1.5} />,
  chat: <MessageSquare className="size-4" strokeWidth={1.5} />,
  settings: <Settings className="size-4" strokeWidth={1.5} />,
};

function JourneyLink({
  item,
  projectId,
  isActive,
}: {
  item: JourneyNavItem;
  projectId: number;
  isActive: boolean;
}) {
  return (
    <NavLink
      to={item.href(projectId)}
      className={cn(
        "group relative flex items-center gap-2 rounded-md py-2 pl-2.5 pr-2 text-[13px] transition-colors",
        isActive
          ? "bg-foreground/[0.04] font-medium text-foreground"
          : "text-muted-foreground/75 hover:bg-foreground/[0.03] hover:text-foreground",
      )}
    >
      {isActive ? (
        <span
          className="absolute inset-y-1.5 left-0 w-[2px] rounded-full bg-primary"
          aria-hidden
        />
      ) : null}
      <span
        className={cn(
          "flex size-4 shrink-0 items-center justify-center transition-colors",
          isActive
            ? "text-primary"
            : "text-muted-foreground/45 group-hover:text-muted-foreground/70",
        )}
      >
        {ICONS[item.id]}
      </span>
      <span className="min-w-0 truncate leading-none">{item.label}</span>
    </NavLink>
  );
}

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
      className="writing-studio-nav flex h-full w-[10.5rem] shrink-0 flex-col border-r border-border/50 bg-muted/45"
      data-testid="project-journey-sidebar"
      aria-label="Project workspace"
    >
      <nav className="flex flex-1 flex-col overflow-y-auto px-2 pb-3 pt-5">
        <p className="mb-2 px-2.5 text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground/55">
          Workspace
        </p>

        <div className="flex flex-col gap-1">
          {PROJECT_JOURNEY_WORKFLOW.map((item) => (
            <JourneyLink
              key={item.id}
              item={item}
              projectId={currentProjectId}
              isActive={active === item.id}
            />
          ))}
        </div>

        <div
          className="mx-2.5 my-4 h-px bg-border/60"
          role="separator"
          aria-hidden
        />

        <div className="flex flex-col gap-1">
          {PROJECT_JOURNEY_SECONDARY.map((item) => (
            <JourneyLink
              key={item.id}
              item={item}
              projectId={currentProjectId}
              isActive={active === item.id}
            />
          ))}
        </div>
      </nav>

      <div className="border-t border-border/40 px-2 py-3">
        <NavLink
          to="/settings"
          className={cn(
            "group relative flex items-center gap-2 rounded-md py-2 pl-2.5 pr-2 text-[13px] transition-colors",
            active === "settings"
              ? "bg-foreground/[0.04] font-medium text-foreground"
              : "text-muted-foreground/65 hover:bg-foreground/[0.03] hover:text-foreground",
          )}
        >
          {active === "settings" ? (
            <span
              className="absolute inset-y-1.5 left-0 w-[2px] rounded-full bg-primary"
              aria-hidden
            />
          ) : null}
          <span
            className={cn(
              "flex size-4 shrink-0 items-center justify-center",
              active === "settings"
                ? "text-primary"
                : "text-muted-foreground/45 group-hover:text-muted-foreground/70",
            )}
          >
            <Settings className="size-4" strokeWidth={1.5} />
          </span>
          <span className="leading-none">Settings</span>
        </NavLink>
      </div>
    </aside>
  );
}
