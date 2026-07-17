import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogFooter,
  DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input }    from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label }    from "@/components/ui/label";
import { Button }   from "@/components/ui/button";
import { useCreateNote, useUpdateNote } from "../useNotes";
import { toast } from "@/components/common/Toast";
import type { Note } from "@/types/api";

interface NoteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  note?: Note | null;          // null/undefined = create mode
  projectId?: number | null;
  fileId?: number | null;
}

export function NoteDialog({
  open,
  onOpenChange,
  note,
  projectId,
  fileId,
}: NoteDialogProps) {
  const createNote = useCreateNote();
  const updateNote = useUpdateNote();

  const [title,   setTitle]   = useState("");
  const [content, setContent] = useState("");

  useEffect(() => {
    if (open) {
      setTitle(note?.title   ?? "");
      setContent(note?.content ?? "");
    }
  }, [open, note]);

  async function save() {
    const trimmedContent = content.trim();
    if (!trimmedContent) {
      toast.error("Note content cannot be empty.");
      return;
    }
    try {
      if (note) {
        await updateNote.mutateAsync({
          id:   note.id,
          body: { title: title.trim(), content: trimmedContent },
        });
        toast.success("Note updated");
      } else {
        await createNote.mutateAsync({
          title:      title.trim(),
          content:    trimmedContent,
          project_id: projectId ?? null,
          file_id:    fileId    ?? null,
        });
        toast.success("Note saved");
      }
      onOpenChange(false);
    } catch {
      toast.error("Could not save note");
    }
  }

  const isBusy = createNote.isPending || updateNote.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{note ? "Edit note" : "New note"}</DialogTitle>
        </DialogHeader>

        <div className="grid gap-3">
          <div className="grid gap-1.5">
            <Label>Title <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <Input
              value={title}
              placeholder="Give this note a heading…"
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") e.preventDefault(); }}
            />
          </div>
          <div className="grid gap-1.5">
            <Label>Content</Label>
            <Textarea
              value={content}
              placeholder="Write your note here…"
              onChange={(e) => setContent(e.target.value)}
              className="min-h-36 resize-y"
              autoFocus
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={isBusy || !content.trim()}>
            {isBusy ? "Saving…" : "Save note"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
