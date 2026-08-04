import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  MessagesSquare, FileText, Brain, Pencil,
  ArrowRight,
} from "lucide-react";
import type { Project } from "@/types/api";

/**
 * Dense project row — answers “What am I working on?” (Design Language).
 * Hairlines only; no card elevation (Border Doctrine).
 */
export function ProjectCard({
  project,
  chatCount,
  fileCount,
  memoryCount,
  onEdit,
}: {
  project: Project;
  chatCount: number;
  fileCount: number;
  memoryCount: number;
  onOpen: () => void;
  onEdit: () => void;
}) {
  const navigate = useNavigate();

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className="group relative flex cursor-pointer items-start gap-3 border-b border-border px-1 py-3 transition-colors last:border-b-0 hover:bg-muted/30"
      data-density="high"
      onClick={() => navigate(`/projects/${project.id}`)}
    >
      <div className="flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-muted/40 text-lg">
        {project.emoji}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start gap-2">
          <h3 className="min-w-0 flex-1 truncate text-[13px] font-medium leading-snug tracking-tight">
            {project.name}
          </h3>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-foreground group-hover:opacity-100 focus-visible:opacity-100"
            title="Edit project"
          >
            <Pencil className="size-3.5" />
          </button>
        </div>
        {project.description ? (
          <p className="mt-0.5 line-clamp-1 text-[12px] text-muted-foreground">
            {project.description}
          </p>
        ) : project.instructions ? (
          <p className="mt-0.5 line-clamp-1 text-[12px] italic text-muted-foreground">
            {project.instructions}
          </p>
        ) : null}

        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] tabular-nums text-muted-foreground">
          <span className="inline-flex items-center gap-1" title="Chats">
            <MessagesSquare className="size-3" /> {chatCount}
          </span>
          <span className="inline-flex items-center gap-1" title="Papers">
            <FileText className="size-3" /> {fileCount}
          </span>
          {memoryCount > 0 && (
            <span className="inline-flex items-center gap-1 text-primary" title="Memories">
              <Brain className="size-3" /> {memoryCount}
            </span>
          )}
          <span className="ml-auto inline-flex items-center gap-1 text-primary opacity-0 transition-opacity group-hover:opacity-100">
            Open <ArrowRight className="size-3" />
          </span>
        </div>
      </div>
    </motion.div>
  );
}
