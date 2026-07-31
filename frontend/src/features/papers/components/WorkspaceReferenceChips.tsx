import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { formatLabel } from "../mappers/shared";
import type { WorkspaceReference, WorkspaceTab } from "../mappers/chat";
import { groupWorkspaceReferences } from "../mappers/chat";

const TAB_LABEL: Record<WorkspaceTab, string> = {
  structure: "Structure",
  classification: "Profile",
  entities: "Entities",
  evidence: "Evidence",
  graph: "Graph",
};

export function WorkspaceReferenceChips({
  references,
  className,
}: {
  references: WorkspaceReference[];
  className?: string;
}) {
  if (!references.length) return null;

  const groups = groupWorkspaceReferences(references);

  return (
    <div className={cn("min-w-0 space-y-3", className)} aria-label="Workspace references">
      {(Object.keys(groups) as WorkspaceTab[]).map((tab) => {
        const items = groups[tab];
        if (!items.length) return null;
        return (
          <div key={tab} className="min-w-0 space-y-1.5">
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              {TAB_LABEL[tab]}
            </p>
            <ul className="flex min-w-0 flex-col gap-1" role="list">
              {items.map((ref) => (
                <li key={ref.id} className="min-w-0">
                  <Link
                    to={ref.href ?? `#`}
                    aria-label={`Open ${ref.label ?? ref.refId} in ${TAB_LABEL[tab]}`}
                    className={cn(
                      "flex w-full min-w-0 items-center rounded-md border border-border bg-card px-2 py-1 text-[12px] text-foreground",
                      "hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    )}
                    title={ref.label ?? ref.kind}
                  >
                    <span className="truncate">{ref.label ?? formatLabel(ref.refId)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
