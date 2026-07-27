import { Link } from "react-router-dom";
import { FileText, FolderKanban, Library } from "lucide-react";
import { useFiles } from "@/features/files/useFiles";
import { useProjects } from "@/features/projects/useProjects";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/**
 * D6 T3 — Project inquiry rail for scoped global chat.
 * Jump into papers / project — not a second chatbot.
 */
export function ProjectInquiryRail({
  projectId,
  className,
}: {
  projectId: number;
  className?: string;
}) {
  const { data: projects = [] } = useProjects();
  const project = projects.find((p) => p.id === projectId);
  const { data: listData, isLoading } = useFiles({
    kind: "document",
    project_id: projectId,
    sort: "recent",
    limit: 8,
  });
  const papers = listData?.items ?? [];

  return (
    <aside
      aria-label="Project workspace"
      className={cn("flex h-full min-h-0 min-w-0 flex-col overflow-hidden", className)}
    >
      <div className="min-h-0 flex-1 space-y-3 overflow-x-hidden overflow-y-auto">
        <div>
          <h2 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Project context
          </h2>
          {project ? (
            <Link
              to={`/projects/${projectId}`}
              className="mt-1.5 flex items-center gap-2 rounded-md px-1.5 py-1 text-[13px] font-medium hover:bg-muted/50"
            >
              <span className="text-base leading-none">{project.emoji}</span>
              <span className="min-w-0 truncate">{project.name}</span>
            </Link>
          ) : (
            <p className="mt-1 flex items-center gap-1.5 text-[13px] text-muted-foreground">
              <FolderKanban className="size-3.5" /> Project #{projectId}
            </p>
          )}
          <p className="mt-1 text-[12px] leading-snug text-muted-foreground">
            Answers retrieve from this project&apos;s papers only.
          </p>
        </div>

        <div className="border-t border-border pt-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Papers
            </p>
            <Link
              to="/library"
              className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
            >
              <Library className="size-3" /> Library
            </Link>
          </div>
          {isLoading ? (
            <div className="space-y-2" aria-busy="true">
              <Skeleton className="h-7 w-full" />
              <Skeleton className="h-7 w-4/5" />
            </div>
          ) : papers.length === 0 ? (
            <p className="text-[12px] text-muted-foreground">
              No papers yet. Upload in Library with this project scoped.
            </p>
          ) : (
            <ul className="flex flex-col gap-0.5" role="list">
              {papers.map((p) => (
                <li key={p.id} className="min-w-0">
                  <Link
                    to={`/papers/${p.id}`}
                    className="flex min-w-0 items-center gap-2 rounded-md px-1.5 py-1.5 text-[12px] hover:bg-muted/50"
                    title={p.title || p.name}
                  >
                    <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate">{p.title || p.name}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </aside>
  );
}
