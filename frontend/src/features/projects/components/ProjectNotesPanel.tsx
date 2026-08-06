import { useMemo, useState } from "react";
import { Pencil, Plus, StickyNote, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { NoteDialog } from "@/features/notes/components/NoteDialog";
import { useDeleteNote, useNotes } from "@/features/notes/useNotes";
import { toast } from "@/components/common/Toast";
import { formatDate } from "@/lib/utils";
import type { Note } from "@/types/api";
import type { NoteSuggestion } from "../noteSuggestions";
import { ProjectNoteSuggestions } from "./ProjectNoteSuggestions";

function NoteCard({
  note,
  onEdit,
  onDelete,
}: {
  note: Note;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const preview =
    note.content.length > 280 ? note.content.slice(0, 280).trimEnd() + "…" : note.content;

  return (
    <div className="group rounded-xl border border-border px-3 py-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium truncate">{note.title || "Untitled note"}</p>
        <div className="flex shrink-0 gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            type="button"
            onClick={onEdit}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted"
            aria-label="Edit note"
          >
            <Pencil className="size-3.5" />
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-destructive"
            aria-label="Delete note"
          >
            <Trash2 className="size-3.5" />
          </button>
        </div>
      </div>
      <p className="text-sm text-muted-foreground whitespace-pre-wrap line-clamp-4">{preview}</p>
      {note.updated_at && (
        <p className="text-[10px] text-muted-foreground/70">{formatDate(note.updated_at)}</p>
      )}
    </div>
  );
}

/** Lazy-loaded notes tab — user-authored only (not AI insights). */
export function ProjectNotesPanel({ projectId }: { projectId: number }) {
  const { data, isLoading } = useNotes({ project_id: projectId, limit: 500 });
  const deleteNote = useDeleteNote();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Note | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftContent, setDraftContent] = useState("");
  const [draftFileId, setDraftFileId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Note | null>(null);

  const notes = useMemo(() => data?.items ?? [], [data?.items]);

  function openCreate() {
    setEditing(null);
    setDraftTitle("");
    setDraftContent("");
    setDraftFileId(null);
    setDialogOpen(true);
  }

  function openEdit(note: Note) {
    setEditing(note);
    setDraftTitle("");
    setDraftContent("");
    setDraftFileId(null);
    setDialogOpen(true);
  }

  function reviewSuggestion(s: NoteSuggestion) {
    setEditing(null);
    setDraftTitle(s.title);
    setDraftContent(s.content);
    setDraftFileId(s.fileId);
    setDialogOpen(true);
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">Notes ({data?.total ?? notes.length})</h2>
          <p className="text-xs text-muted-foreground">
            Your writing — save suggestions below or create notes manually.
          </p>
        </div>
        <Button size="sm" className="gap-1.5" onClick={openCreate}>
          <Plus className="size-3.5" /> New note
        </Button>
      </div>

      <ProjectNoteSuggestions
        projectId={projectId}
        notes={notes}
        onReviewSuggestion={reviewSuggestion}
      />

      <section className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Your notes
        </h3>
        {notes.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border px-6 py-10 text-center space-y-2">
            <StickyNote className="mx-auto size-8 text-muted-foreground" />
            <p className="text-sm font-medium">No notes yet</p>
            <p className="text-xs text-muted-foreground">
              Save a suggested highlight above, or capture your own observations as you read.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {notes.map((n) => (
              <NoteCard
                key={n.id}
                note={n}
                onEdit={() => openEdit(n)}
                onDelete={() => setDeleteTarget(n)}
              />
            ))}
          </div>
        )}
      </section>

      <NoteDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        note={editing}
        projectId={projectId}
        fileId={draftFileId}
        initialTitle={editing ? undefined : draftTitle}
        initialContent={editing ? undefined : draftContent}
      />

      <ConfirmDialog
        open={deleteTarget != null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete note?"
        entityName={deleteTarget?.title || deleteTarget?.content?.slice(0, 80) || null}
        description="This note will be permanently removed from the project."
        confirmLabel="Delete note"
        cancelLabel="Keep note"
        destructive
        onConfirm={async () => {
          if (!deleteTarget) return;
          await deleteNote.mutateAsync(deleteTarget.id);
          toast.success("Note deleted");
          setDeleteTarget(null);
        }}
      />
    </div>
  );
}
