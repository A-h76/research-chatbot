/**
 * Progressive disclosure for project identity — metrics on demand, not always-on.
 */
import { useNavigate } from "react-router-dom";
import {
  FileText,
  StickyNote,
  Brain,
  PenLine,
  LayoutDashboard,
  Settings2,
  Download,
} from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useProjectHub } from "../useProjects";
import { projectExportUrl, projectHubUrl, projectWritingUrl } from "../projectWorkspaceNav";
import { cn } from "@/lib/utils";

function StatRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <div className="flex items-center justify-between gap-3 px-1 py-1 text-[12px]">
      <span className="flex items-center gap-2 text-muted-foreground">
        <span className="text-foreground/70">{icon}</span>
        {label}
      </span>
      <span className="tabular-nums font-medium text-foreground">{value}</span>
    </div>
  );
}

export function ProjectOverviewPopover({
  projectId,
  children,
  className,
}: {
  projectId: number;
  children: React.ReactNode;
  className?: string;
}) {
  const navigate = useNavigate();
  const { data: hub } = useProjectHub(projectId);
  const stats = hub?.stats;
  const analysis = hub?.analysis_summary;
  const ready = analysis?.ready ?? 0;
  const papers = stats?.papers ?? 0;
  const progress =
    papers > 0 ? Math.round((ready / Math.max(papers, 1)) * 100) : 0;

  return (
    <Popover>
      <PopoverTrigger
        className={cn(
          "inline-flex min-w-0 max-w-[28ch] items-center gap-1 rounded-md px-1.5 py-1 text-left text-[13px] font-medium text-foreground outline-none transition-colors hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring",
          className,
        )}
      >
        {children}
      </PopoverTrigger>
      <PopoverContent align="start" className="w-72 gap-1 p-2" sideOffset={8}>
        <div className="px-1.5 pb-1.5 pt-0.5">
          <p className="truncate text-[13px] font-semibold text-foreground">
            {hub?.project.emoji} {hub?.project.name ?? "Project"}
          </p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">Overview</p>
        </div>

        <div className="rounded-md bg-muted/40 px-1.5 py-1">
          <StatRow
            icon={<FileText className="size-3.5" />}
            label="Papers"
            value={papers}
          />
          <StatRow
            icon={<StickyNote className="size-3.5" />}
            label="Notes"
            value={stats?.notes ?? 0}
          />
          <StatRow
            icon={<Brain className="size-3.5" />}
            label="Evidence ready"
            value={`${ready}/${papers}`}
          />
          <StatRow
            icon={<PenLine className="size-3.5" />}
            label="Writing progress"
            value={`${progress}%`}
          />
          <StatRow
            icon={<LayoutDashboard className="size-3.5" />}
            label="Status"
            value={
              papers === 0
                ? "Add papers"
                : ready < 2
                  ? "Analysing"
                  : "Ready to write"
            }
          />
        </div>

        <div className="mt-1 flex flex-col gap-0.5 border-t border-border/60 pt-1.5">
          <button
            type="button"
            className="rounded-md px-2 py-1.5 text-left text-[12px] text-foreground hover:bg-muted"
            onClick={() => navigate(projectHubUrl(projectId))}
          >
            Open project dashboard
          </button>
          <button
            type="button"
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-[12px] text-foreground hover:bg-muted"
            onClick={() => navigate(projectWritingUrl(projectId))}
          >
            <PenLine className="size-3.5 text-muted-foreground" /> Continue writing
          </button>
          <button
            type="button"
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-[12px] text-foreground hover:bg-muted"
            onClick={() => navigate(projectExportUrl(projectId))}
          >
            <Download className="size-3.5 text-muted-foreground" /> Export
          </button>
          <button
            type="button"
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-[12px] text-muted-foreground hover:bg-muted hover:text-foreground"
            onClick={() => navigate(projectHubUrl(projectId))}
          >
            <Settings2 className="size-3.5" /> Manage project
          </button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
