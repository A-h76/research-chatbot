import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { BookmarkPlus, FileText, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/common/Toast";
import { useFiles, usePaperAnalyses } from "@/features/files/useFiles";
import { useCreateNote } from "@/features/notes/useNotes";
import { cn } from "@/lib/utils";
import type { Note } from "@/types/api";
import { isCrossPaperResearchReady } from "../crossPaperResearchReady";
import {
  collectProjectNoteSuggestions,
  filterSavedNoteSuggestions,
  type NoteSuggestion,
} from "../noteSuggestions";

function SuggestionCard({
  suggestion,
  busy,
  onSave,
  onDismiss,
  onReview,
}: {
  suggestion: NoteSuggestion;
  busy: boolean;
  onSave: () => void;
  onDismiss: () => void;
  onReview: () => void;
}) {
  return (
    <div className="rounded-xl border border-dashed border-primary/25 bg-accent-soft/20 px-3 py-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="rounded-md bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
              {suggestion.section}
            </span>
            <Link
              to={`/papers/${suggestion.fileId}`}
              className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline truncate max-w-[14rem]"
            >
              <FileText className="size-3 shrink-0" />
              {suggestion.paperTitle}
            </Link>
          </div>
          <p className="text-sm text-foreground/90 leading-relaxed line-clamp-4">
            {suggestion.excerpt}
          </p>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Dismiss suggestion"
        >
          <X className="size-3.5" />
        </button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Button size="sm" className="h-7 gap-1 text-xs" disabled={busy} onClick={onSave}>
          <BookmarkPlus className="size-3" />
          Save as note
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs"
          disabled={busy}
          onClick={onReview}
        >
          Review &amp; edit
        </Button>
      </div>
    </div>
  );
}

export function ProjectNoteSuggestions({
  projectId,
  notes,
  onReviewSuggestion,
}: {
  projectId: number;
  notes: Note[];
  onReviewSuggestion: (suggestion: NoteSuggestion) => void;
}) {
  const createNote = useCreateNote();
  const [dismissed, setDismissed] = useState<Set<string>>(() => new Set());
  const [savingId, setSavingId] = useState<string | null>(null);

  const { data: fileData, isLoading: filesLoading } = useFiles({
    project_id: projectId,
    kind: "document",
    limit: 500,
  });

  const readyFiles = useMemo(
    () => (fileData?.items ?? []).filter(isCrossPaperResearchReady),
    [fileData?.items],
  );
  const readyIds = useMemo(() => readyFiles.map((f) => f.id), [readyFiles]);
  const { byId: analysesById, isLoading: analysesLoading } = usePaperAnalyses(readyIds);

  const suggestions = useMemo(() => {
    const raw = collectProjectNoteSuggestions(readyFiles, analysesById);
    const withoutSaved = filterSavedNoteSuggestions(raw, notes);
    return withoutSaved.filter((s) => !dismissed.has(s.id));
  }, [readyFiles, analysesById, notes, dismissed]);

  async function saveSuggestion(s: NoteSuggestion) {
    setSavingId(s.id);
    try {
      await createNote.mutateAsync({
        title: s.title,
        content: s.content,
        project_id: projectId,
        file_id: s.fileId,
      });
      toast.success("Saved to your notes");
      setDismissed((prev) => new Set(prev).add(s.id));
    } catch {
      toast.error("Could not save note");
    } finally {
      setSavingId(null);
    }
  }

  if (filesLoading || analysesLoading) {
    return (
      <section className="space-y-2">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-20 w-full rounded-xl" />
      </section>
    );
  }

  if (readyFiles.length === 0) {
    return (
      <section className="rounded-xl border border-dashed border-border px-4 py-3 text-xs text-muted-foreground">
        <div className="flex items-center gap-2 font-medium text-foreground">
          <Sparkles className="size-3.5 text-primary" />
          Suggested highlights
        </div>
        <p className="mt-1">
          Appear after papers finish structured analysis — upload in Papers and wait for
          Research Profile / Structure to complete.
        </p>
      </section>
    );
  }

  if (suggestions.length === 0) {
    return null;
  }

  return (
    <section className={cn("space-y-3")}>
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
          <Sparkles className="size-3.5 text-primary" />
          Suggested from your papers ({suggestions.length})
        </h3>
        <p className="text-[11px] text-muted-foreground mt-0.5">
          Passages worth saving — pulled from analysis, not written into your notes until
          you choose Save.
        </p>
      </div>
      <div className="space-y-2">
        {suggestions.map((s) => (
          <SuggestionCard
            key={s.id}
            suggestion={s}
            busy={createNote.isPending && savingId === s.id}
            onSave={() => void saveSuggestion(s)}
            onDismiss={() => setDismissed((prev) => new Set(prev).add(s.id))}
            onReview={() => onReviewSuggestion(s)}
          />
        ))}
      </div>
    </section>
  );
}
