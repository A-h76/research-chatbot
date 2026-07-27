import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  ImageIcon,
  Trash2,
  CheckCircle2,
  BookOpen,
  BookMarked,
  Upload,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { AiStateBadge, type AiStateResolved } from "@/features/pipeline";
import { toast } from "@/components/common/Toast";
import type { Project, UserFile } from "@/types/api";
import { libraryBridgeApi } from "../libraryBridgeApi";

const STATUS_ICONS = {
  unread: BookOpen,
  reading: BookMarked,
  read: CheckCircle2,
};

/**
 * D5 — Dense Library row (GitHub-like). Prefer over card grid.
 */
export function FileCard({
  file,
  project,
  onDelete,
  aiState,
}: {
  file: UserFile;
  project?: Project;
  onDelete: () => void;
  aiState?: AiStateResolved;
}) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const rs = (file.reading_status ?? "unread") as "unread" | "reading" | "read";
  const StatusIcon = STATUS_ICONS[rs];
  const isPaper = file.kind === "document";
  const readiness = file.research_readiness;
  const metadataOnly =
    isPaper &&
    (readiness === "metadata_only" ||
      file.has_pdf === false ||
      (!readiness && (file.size === 0 || !file.size)));
  const displayTitle = file.title || file.name;
  const meta = [file.authors?.split(";")[0]?.trim(), file.year]
    .filter(Boolean)
    .join(" · ");

  const attachPdf = async (pdf: File) => {
    try {
      await libraryBridgeApi.attachPdf(file.id, pdf);
      toast.success("PDF attached — analysis queued");
      void qc.invalidateQueries({ queryKey: ["files"] });
      void qc.invalidateQueries({ queryKey: ["library"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not attach PDF");
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => {
        if (isPaper) navigate(`/papers/${file.id}`);
      }}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && isPaper) {
          e.preventDefault();
          navigate(`/papers/${file.id}`);
        }
      }}
      className="group flex w-full items-center gap-3 border-b border-border px-2 py-2.5 text-left transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring last:border-b-0"
    >
      <div
        className={cn(
          "flex size-8 shrink-0 items-center justify-center rounded-md",
          isPaper ? "bg-muted" : "bg-muted",
        )}
      >
        {file.kind === "image" ? (
          <ImageIcon className="size-4 text-muted-foreground" />
        ) : (
          <FileText className="size-4 text-muted-foreground" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium leading-snug" title={displayTitle}>
          {displayTitle}
        </p>
        <p className="mt-0.5 truncate text-[12px] text-muted-foreground">
          {meta || (file.title && file.title !== file.name ? file.name : "No metadata yet")}
          {project ? ` · ${project.emoji} ${project.name}` : ""}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {isPaper && readiness && readiness !== "research_ready" && (
          <span
            className="hidden rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground sm:inline"
            title={file.research_readiness_label || readiness}
          >
            {file.research_readiness_label || readiness.replace(/_/g, " ")}
          </span>
        )}
        {metadataOnly && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => {
                const pdf = e.target.files?.[0];
                if (pdf) void attachPdf(pdf);
                e.target.value = "";
              }}
            />
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
              className="hidden items-center gap-1 rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground hover:text-foreground sm:inline-flex"
              title="Attach PDF to analyse"
            >
              <Upload className="size-3" /> PDF
            </button>
          </>
        )}
        {isPaper && <AiStateBadge state={aiState} metaStatus={file.meta_status} />}
        {isPaper && (
          <span
            className="hidden items-center gap-1 text-[11px] text-muted-foreground sm:inline-flex"
            title={rs}
          >
            <StatusIcon className="size-3" />
            <span className="capitalize">{rs}</span>
          </span>
        )}
        {file.tags?.length > 0 && (
          <span className="hidden max-w-[8rem] truncate rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground md:inline">
            {file.tags[0]}
            {file.tags.length > 1 ? ` +${file.tags.length - 1}` : ""}
          </span>
        )}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="rounded-md p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-muted hover:text-destructive group-hover:opacity-100 focus:opacity-100"
          title="Delete"
        >
          <Trash2 className="size-3.5" />
        </button>
      </div>
    </div>
  );
}
