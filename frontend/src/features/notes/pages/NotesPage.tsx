import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus, Search, StickyNote, Pencil, Trash2,
  FolderKanban, FileText, X, Clock,
} from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button }        from "@/components/ui/button";
import { EmptyState }    from "@/components/common/EmptyState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { NoteDialog }    from "../components/NoteDialog";
import { useDeleteNote, useNotes } from "../useNotes";
import { useProjects }   from "@/features/projects/useProjects";
import { useUI }         from "@/context/UIContext";
import { toast }         from "@/components/common/Toast";
import { cn, formatDate } from "@/lib/utils";
import type { Note } from "@/types/api";

// ── Note card ────────────────────────────────────────────────────────────────
function NoteCard({
  note,
  projectName,
  onEdit,
  onDelete,
}: {
  note: Note;
  projectName?: string;
  onEdit:   () => void;
  onDelete: () => void;
}) {
  // Show first 280 chars of content as a preview
  const preview = note.content.length > 280
    ? note.content.slice(0, 280).trimEnd() + "…"
    : note.content;

  const isPaperNote = note.file_id !== null;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.15 }}
      className="group flex flex-col gap-2 border-b border-border py-4 text-left last:border-b-0"
      data-density="low"
    >
      {/* Top row: title + action buttons */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          {note.title ? (
            <h3 className="truncate text-[15px] font-medium leading-snug tracking-tight" title={note.title}>
              {note.title}
            </h3>
          ) : (
            <h3 className="text-[15px] font-medium italic text-muted-foreground">Untitled</h3>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
          <button
            onClick={onEdit}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            title="Edit"
          >
            <Pencil className="size-3.5" />
          </button>
          <button
            onClick={onDelete}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-destructive"
            title="Delete"
          >
            <Trash2 className="size-3.5" />
          </button>
        </div>
      </div>

      {/* Content preview — Notion reading measure */}
      <p className="max-w-[65ch] text-[15px] leading-[1.55] text-foreground/85 whitespace-pre-wrap break-words">
        {preview}
      </p>

      {/* Footer: meta chips + timestamp */}
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
        {isPaperNote && (
          <span className="inline-flex items-center gap-1 rounded border border-border px-1.5 py-0.5 text-primary">
            <FileText className="size-3" /> Paper note
          </span>
        )}
        {projectName && (
          <span className="inline-flex items-center gap-1 rounded border border-border px-1.5 py-0.5">
            <FolderKanban className="size-3" />
            <span className="max-w-[12ch] truncate">{projectName}</span>
          </span>
        )}
        <span className="ml-auto inline-flex items-center gap-1 tabular-nums">
          <Clock className="size-3" />
          {note.updated_at ? formatDate(note.updated_at) : "—"}
        </span>
      </div>
    </motion.div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export function NotesPage() {
  const { currentProjectId } = useUI();
  const [searchParams]       = useSearchParams();
  const { data: projects = [] } = useProjects();
  const deleteNote              = useDeleteNote();

  // Filter state
  const [q,           setQ]           = useState(searchParams.get("q") ?? "");
  const [projectFilter, setProjectFilter] = useState<number | null | "all">(
    currentProjectId ?? "all"
  );
  const [dialogOpen,  setDialogOpen]  = useState(false);
  const [editing,     setEditing]     = useState<Note | null>(null);
  const [toDelete,    setToDelete]    = useState<Note | null>(null);

  // Build query params
  const listParams = {
    project_id: projectFilter !== "all" ? projectFilter : undefined,
    q:          q.trim() || undefined,
    limit:      200,
  };

  const { data: listData, isLoading } = useNotes(listParams);
  const notes = listData?.items ?? [];
  const total = listData?.total ?? 0;

  const hasFilters = q.trim() || projectFilter !== "all";

  function openCreate() {
    setEditing(null);
    setDialogOpen(true);
  }

  function openEdit(note: Note) {
    setEditing(note);
    setDialogOpen(true);
  }

  // Project name lookup
  const projectMap = useMemo(() => {
    const m: Record<number, string> = {};
    for (const p of projects) m[p.id] = p.name;
    return m;
  }, [projects]);

  return (
    <PageContainer
      title="Notes"
      description="Capture thoughts linked to your research — one calm reading column."
      actions={
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-1.5">
            <Search className="size-4 shrink-0 text-muted-foreground" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search notes…"
              className="w-36 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            {q && (
              <button onClick={() => setQ("")} className="text-muted-foreground hover:text-foreground">
                <X className="size-3.5" />
              </button>
            )}
          </div>
          <Button onClick={openCreate} className="gap-1.5">
            <Plus className="size-4" /> New note
          </Button>
        </div>
      }
    >
      <div className="space-y-4" data-density="low">
        {/* Project filter tabs */}
        {projects.length > 0 && (
          <div className="flex flex-wrap items-center gap-1 border-b border-border pb-2">
            <button
              onClick={() => setProjectFilter("all")}
              className={cn(
                "rounded-md px-2.5 py-1 text-[13px] font-medium transition-colors",
                projectFilter === "all"
                  ? "bg-accent-soft text-primary"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              All notes
            </button>
            <button
              onClick={() => setProjectFilter(null)}
              className={cn(
                "rounded-md px-2.5 py-1 text-[13px] font-medium transition-colors",
                projectFilter === null
                  ? "bg-accent-soft text-primary"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              Unassigned
            </button>
            {projects.map((p) => (
              <button
                key={p.id}
                onClick={() => setProjectFilter(p.id)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[13px] font-medium transition-colors",
                  projectFilter === p.id
                    ? "bg-accent-soft text-primary"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <span>{p.emoji}</span>
                <span className="max-w-[12ch] truncate">{p.name}</span>
              </button>
            ))}
          </div>
        )}

        {/* Results count */}
        {!isLoading && total > 0 && (
          <p className="text-xs text-muted-foreground">
            {total} note{total !== 1 ? "s" : ""}
            {hasFilters ? " matching" : ""}
          </p>
        )}

        {/* Cards grid */}
        {isLoading ? (
          <div className="max-w-[65ch] space-y-0 divide-y divide-border">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-24 animate-pulse bg-muted/40" />
            ))}
          </div>
        ) : notes.length === 0 ? (
          hasFilters ? (
            <EmptyState
              title="No notes match your search"
              action={
                <Button variant="outline" size="sm" onClick={() => { setQ(""); setProjectFilter("all"); }}>
                  Clear filters
                </Button>
              }
            />
          ) : (
            <EmptyState
              icon={<StickyNote className="size-8" />}
              title="No notes yet"
              description="Capture ideas, annotations, and key takeaways from your papers."
              action={
                <Button onClick={openCreate}>
                  <Plus className="size-4" /> Write your first note
                </Button>
              }
            />
          )
        ) : (
          <div className="max-w-[65ch]">
            <AnimatePresence>
              {notes.map((note) => (
                <NoteCard
                  key={note.id}
                  note={note}
                  projectName={note.project_id ? projectMap[note.project_id] : undefined}
                  onEdit={() => openEdit(note)}
                  onDelete={() => setToDelete(note)}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Create / Edit dialog */}
      <NoteDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        note={editing}
        projectId={
          editing
            ? editing.project_id
            : projectFilter !== "all"
            ? projectFilter
            : currentProjectId
        }
      />

      {/* Delete confirm */}
      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        title="Delete this note?"
        entityName={toDelete?.title || toDelete?.content?.slice(0, 80) || null}
        description="This note will be permanently removed from the project."
        confirmLabel="Delete note"
        cancelLabel="Keep note"
        destructive
        onConfirm={async () => {
          if (!toDelete) return;
          await deleteNote.mutateAsync(toDelete.id);
          toast.success("Note deleted");
          setToDelete(null);
        }}
      />
    </PageContainer>
  );
}
