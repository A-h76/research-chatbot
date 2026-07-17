import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  FileText, ImageIcon, Trash2, CheckCircle2,
  BookOpen, BookMarked, Loader2, ArrowRight,
} from "lucide-react";
import { formatBytes } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { Project, UserFile } from "@/types/api";

const STATUS_COLORS = {
  unread:  "text-muted-foreground",
  reading: "text-amber-600 dark:text-amber-400",
  read:    "text-emerald-600 dark:text-emerald-400",
};

const STATUS_ICONS = {
  unread:  BookOpen,
  reading: BookMarked,
  read:    CheckCircle2,
};

const META_STATUS_LABELS: Record<string, string> = {
  pending: "Extracting…",
  running: "Analysing…",
  done:    "",
  failed:  "Analysis failed",
};

export function FileCard({
  file,
  project,
  onDelete,
}: {
  file: UserFile;
  project?: Project;
  onDelete: () => void;
}) {
  const navigate = useNavigate();
  const rs = (file.reading_status ?? "unread") as "unread" | "reading" | "read";
  const StatusIcon = STATUS_ICONS[rs];
  const isPaper = file.kind === "document";
  const isProcessing = file.meta_status === "pending" || file.meta_status === "running";
  const displayTitle = file.title || file.name;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className="group flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 shadow-sm hover:border-primary/30 hover:shadow-md transition-all"
    >
      {/* Top row: icon + delete */}
      <div className="flex items-start justify-between">
        <div className={cn(
          "flex size-10 items-center justify-center rounded-xl",
          isPaper ? "bg-accent-soft" : "bg-muted",
        )}>
          {file.kind === "image" ? (
            <ImageIcon className="size-5 text-muted-foreground" />
          ) : (
            <FileText className={cn("size-5", isPaper ? "text-primary" : "text-muted-foreground")} />
          )}
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="rounded-md p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-destructive group-hover:opacity-100"
          title="Delete"
        >
          <Trash2 className="size-4" />
        </button>
      </div>

      {/* Title + filename */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium leading-snug" title={displayTitle}>
          {displayTitle}
        </p>
        {file.title && file.title !== file.name && (
          <p className="mt-0.5 truncate text-xs text-muted-foreground" title={file.name}>
            {file.name}
          </p>
        )}
        <p className="mt-0.5 text-xs text-muted-foreground">{formatBytes(file.size)}</p>
      </div>

      {/* Status chips */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {isPaper && (
          <span className={cn("inline-flex items-center gap-1 font-medium", STATUS_COLORS[rs])}>
            <StatusIcon className="size-3" />
            {rs.charAt(0).toUpperCase() + rs.slice(1)}
          </span>
        )}
        {isProcessing && (
          <span className="inline-flex items-center gap-1 text-muted-foreground">
            <Loader2 className="size-3 animate-spin" />
            {META_STATUS_LABELS[file.meta_status]}
          </span>
        )}
        {file.meta_status === "done" && file.kind === "document" && file.chunks > 0 && (
          <span className="inline-flex items-center gap-1 text-primary">
            <CheckCircle2 className="size-3" /> Indexed
          </span>
        )}
        {project && (
          <span className="rounded-full border border-border px-2 py-0.5 text-muted-foreground">
            {project.emoji} {project.name}
          </span>
        )}
      </div>

      {/* Authors + year row */}
      {(file.authors || file.year) && (
        <p className="line-clamp-1 text-xs text-muted-foreground">
          {[file.authors, file.year].filter(Boolean).join(" · ")}
        </p>
      )}

      {/* Tags */}
      {file.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {file.tags.slice(0, 3).map((t) => (
            <span
              key={t}
              className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
            >
              {t}
            </span>
          ))}
          {file.tags.length > 3 && (
            <span className="text-[10px] text-muted-foreground">+{file.tags.length - 3}</span>
          )}
        </div>
      )}

      {/* Open button — only for documents */}
      {isPaper && (
        <button
          onClick={() => navigate(`/papers/${file.id}`)}
          className="mt-auto flex w-full items-center justify-center gap-1.5 rounded-lg border border-border py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:bg-accent-soft hover:text-primary"
        >
          Open paper <ArrowRight className="size-3" />
        </button>
      )}
    </motion.div>
  );
}
