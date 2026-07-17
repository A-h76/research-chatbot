import { useState } from "react";
import { motion } from "framer-motion";
import { Pencil, Trash2, Check, X, Globe } from "lucide-react";
import { ImportanceStars } from "./ImportanceStars";
import { Textarea } from "@/components/ui/textarea";
import { formatDate } from "@/lib/utils";
import type { Memory, Project } from "@/types/api";

export function MemoryCard({
  memory,
  project,
  onUpdate,
  onDelete,
}: {
  memory: Memory;
  project?: Project;
  onUpdate: (body: { fact?: string; importance?: number }) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(memory.fact);

  const save = () => {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== memory.fact) onUpdate({ fact: trimmed });
    setEditing(false);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className="group flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 shadow-sm"
    >
      {editing ? (
        <div className="flex flex-col gap-2">
          <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} className="min-h-20 text-sm" autoFocus />
          <div className="flex justify-end gap-1.5">
            <button
              onClick={() => {
                setDraft(memory.fact);
                setEditing(false);
              }}
              className="rounded-md p-1.5 text-muted-foreground hover:bg-muted"
            >
              <X className="size-4" />
            </button>
            <button onClick={save} className="rounded-md p-1.5 text-primary hover:bg-accent-soft">
              <Check className="size-4" />
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm leading-relaxed">{memory.fact}</p>
          <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
            <button
              onClick={() => setEditing(true)}
              className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              title="Edit"
            >
              <Pencil className="size-3.5" />
            </button>
            <button
              onClick={onDelete}
              className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-destructive"
              title="Forget"
            >
              <Trash2 className="size-3.5" />
            </button>
          </div>
        </div>
      )}
      <div className="mt-auto flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <ImportanceStars value={memory.importance} onChange={(v) => onUpdate({ importance: v })} />
        <div className="flex items-center gap-2">
          {project ? (
            <span className="rounded-full border border-border px-2 py-0.5">
              {project.emoji} {project.name}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5">
              <Globe className="size-3" /> Global
            </span>
          )}
          <span>{formatDate(memory.created_at)}</span>
        </div>
      </div>
    </motion.div>
  );
}
