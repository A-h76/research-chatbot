import { Link } from "react-router-dom";
import { StickyNote } from "lucide-react";
import { useNotes } from "@/features/notes/useNotes";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/utils";

export function WritingNotesTab({ projectId }: { projectId: number | null }) {
  const { data, isLoading } = useNotes(
    projectId != null ? { project_id: projectId, limit: 40 } : {},
  );
  const notes = data?.items ?? [];

  if (projectId == null) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-sm text-muted-foreground">
        Select a project to view notes.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  if (notes.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
        <StickyNote className="size-8 text-muted-foreground" />
        <p className="text-sm font-medium">No notes yet</p>
        <p className="max-w-sm text-xs text-muted-foreground">
          Capture findings while you read. Notes stay linked to this project.
        </p>
        <Link to={`/projects/${projectId}?tab=notes`} className="mt-2 text-xs font-medium text-primary hover:underline">
          Open project notes →
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-4">
      {notes.map((n) => (
        <div key={n.id} className="rounded-md border border-border bg-card px-3 py-2.5">
          <p className="text-sm font-medium">{n.title || "Untitled note"}</p>
          <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
            {n.content?.slice(0, 160) || "Empty"}
          </p>
          {n.updated_at || n.created_at ? (
            <p className="mt-1 text-[10px] text-muted-foreground">
              {formatDate(n.updated_at || n.created_at || "")}
            </p>
          ) : null}
        </div>
      ))}
      <Link
        to={`/projects/${projectId}?tab=notes`}
        className="inline-block pt-1 text-xs font-medium text-primary hover:underline"
      >
        Manage all notes →
      </Link>
    </div>
  );
}
