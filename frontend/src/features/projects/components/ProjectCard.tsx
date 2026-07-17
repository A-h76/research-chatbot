import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  MessagesSquare, FileText, Brain, Pencil,
  ArrowRight,
} from "lucide-react";
import type { Project } from "@/types/api";

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
  onOpen: () => void;   // kept for backwards compat; navigation now uses router
  onEdit: () => void;
}) {
  const navigate = useNavigate();

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.18 }}
      className="group relative flex cursor-pointer flex-col gap-3 rounded-2xl border border-border bg-card p-5 shadow-sm transition-all hover:border-primary/30 hover:shadow-md"
      onClick={() => navigate(`/projects/${project.id}`)}
    >
      {/* Edit button */}
      <button
        onClick={(e) => { e.stopPropagation(); onEdit(); }}
        className="absolute right-3 top-3 rounded-md p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-foreground group-hover:opacity-100"
        title="Edit project"
      >
        <Pencil className="size-3.5" />
      </button>

      {/* Emoji */}
      <div className="flex size-11 items-center justify-center rounded-xl bg-accent-soft text-2xl">
        {project.emoji}
      </div>

      {/* Name + description */}
      <div className="min-w-0">
        <h3 className="font-medium leading-snug">{project.name}</h3>
        {project.description && (
          <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
            {project.description}
          </p>
        )}
        {!project.description && project.instructions && (
          <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground italic">
            {project.instructions}
          </p>
        )}
      </div>

      {/* Stats row */}
      <div className="mt-auto flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1" title="Chats">
          <MessagesSquare className="size-3.5" /> {chatCount}
        </span>
        <span className="inline-flex items-center gap-1" title="Papers">
          <FileText className="size-3.5" /> {fileCount}
        </span>
        {memoryCount > 0 && (
          <span className="inline-flex items-center gap-1 text-primary" title="Memories">
            <Brain className="size-3.5" /> {memoryCount}
          </span>
        )}
        <span className="ml-auto flex items-center gap-1 text-primary opacity-0 transition-opacity group-hover:opacity-100">
          Open <ArrowRight className="size-3" />
        </span>
      </div>
    </motion.div>
  );
}
