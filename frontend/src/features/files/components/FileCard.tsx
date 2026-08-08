import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Trash2,
  Upload,
  MessageSquare,
  GitCompare,
  FolderPlus,
  ArrowRight,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import type { AiStateResolved } from "@/features/pipeline";
import { toast } from "@/components/common/Toast";
import type { Project, UserFile } from "@/types/api";
import { libraryBridgeApi } from "../libraryBridgeApi";

const STUDY_HINTS = [
  "rct",
  "randomized",
  "randomised",
  "cohort",
  "case-control",
  "case report",
  "meta-analysis",
  "systematic review",
  "review",
  "cross-sectional",
  "qualitative",
  "in vitro",
  "in vivo",
  "observational",
];

function studyTypeLabel(file: UserFile): string | null {
  for (const t of file.tags ?? []) {
    const low = t.toLowerCase();
    if (STUDY_HINTS.some((h) => low.includes(h))) return t;
  }
  return null;
}

function relativeAdded(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  const days = Math.floor((Date.now() - t) / 86_400_000);
  if (days <= 0) return "Added today";
  if (days === 1) return "Added yesterday";
  if (days < 7) return `Added ${days}d ago`;
  if (days < 30) return `Added ${Math.floor(days / 7)}w ago`;
  return null;
}

/** One human status — never Profile / Evidence / Chat engineering chips. */
function humanStatus(
  file: UserFile,
): { label: string; tone: "ready" | "warn" | "muted" } | null {
  const rs = (file.reading_status ?? "unread") as "unread" | "reading" | "read";
  const metadataOnly =
    file.kind === "document" &&
    (file.research_readiness === "metadata_only" ||
      file.has_pdf === false ||
      (!file.research_readiness && (file.size === 0 || !file.size)));

  if (file.meta_status === "failed") return { label: "Import failed", tone: "warn" };
  if (file.meta_status === "pending" || file.meta_status === "running") {
    return { label: "Processing", tone: "muted" };
  }
  if (metadataOnly) return { label: "Needs PDF", tone: "warn" };
  if (rs === "reading") return { label: "Reading", tone: "muted" };
  if (rs === "unread") return { label: "Unread", tone: "muted" };
  if (rs === "read") return { label: "Read", tone: "muted" };
  return null;
}

/**
 * Library row — research object, not a database/admin record.
 */
export function FileCard({
  file,
  project,
  onDelete,
  aiState: _aiState,
  selected = false,
  onToggleSelect,
  showProject = true,
}: {
  file: UserFile;
  project?: Project;
  onDelete: () => void;
  aiState?: AiStateResolved;
  selected?: boolean;
  onToggleSelect?: (id: number) => void;
  /** Hide project chip when Library is already scoped to that project. */
  showProject?: boolean;
}) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isPaper = file.kind === "document";
  const readiness = file.research_readiness;
  const metadataOnly =
    isPaper &&
    (readiness === "metadata_only" ||
      file.has_pdf === false ||
      (!readiness && (file.size === 0 || !file.size)));
  const displayTitle = file.title || file.name;
  const authors = file.authors?.split(";")[0]?.trim();
  const study = studyTypeLabel(file);
  const status = isPaper ? humanStatus(file) : null;
  const added = relativeAdded(file.created_at);

  const metaParts = [
    authors,
    file.venue ? file.venue : null,
    file.year,
    study,
    showProject && project ? `${project.emoji} ${project.name}` : null,
  ].filter(Boolean);

  const attachPdf = async (pdf: File) => {
    try {
      const res = await libraryBridgeApi.attachPdf(file.id, pdf);
      if (res.queued) {
        toast.success("PDF attached — analysis queued");
      } else {
        toast.success("PDF attached — open the paper to start analysis if it does not begin");
      }
      void qc.invalidateQueries({ queryKey: ["files"] });
      void qc.invalidateQueries({ queryKey: ["library"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not attach PDF");
    }
  };

  const pullFromRefMgr = async () => {
    try {
      const res = await libraryBridgeApi.pullPdf(file.id);
      if (res.pulled && res.pulled > 0) {
        toast.success(
          res.queued
            ? "PDF pulled from library — analysis queued"
            : "PDF pulled from library",
        );
      } else if (res.skipped?.length) {
        toast.error("No PDF attachment found in Zotero/Mendeley for this paper");
      } else {
        toast.error(res.detail || res.error || "Could not pull PDF");
      }
      void qc.invalidateQueries({ queryKey: ["files"] });
      void qc.invalidateQueries({ queryKey: ["library"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not pull PDF");
    }
  };

  const canPullRefMgr =
    metadataOnly &&
    (file.external_provider === "zotero" || file.external_provider === "mendeley") &&
    Boolean(file.external_item_id);

  const open = () => {
    if (isPaper) navigate(`/papers/${file.id}`);
  };

  return (
    <div
      className={cn(
        "group relative flex w-full items-start gap-2.5 border-b border-border px-1 py-3 text-left transition-colors last:border-b-0",
        selected ? "bg-primary/[0.04]" : "hover:bg-muted/40",
      )}
      data-density="high"
    >
      {isPaper && onToggleSelect && (
        <label className="mt-1 flex shrink-0 cursor-pointer items-center">
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggleSelect(file.id)}
            onClick={(e) => e.stopPropagation()}
            className="size-3.5 rounded border-border accent-primary"
            aria-label={`Select ${displayTitle}`}
          />
        </label>
      )}

      <button
        type="button"
        onClick={open}
        className="min-w-0 flex-1 text-left focus-visible:outline-none"
      >
        <p
          className="line-clamp-2 text-[14px] font-semibold leading-snug tracking-tight text-text-primary"
          title={displayTitle}
        >
          {displayTitle}
        </p>
        <p className="mt-0.5 truncate text-[12px] text-text-secondary">
          {metaParts.length
            ? metaParts.join(" · ")
            : file.title && file.title !== file.name
              ? file.name
              : "No metadata yet"}
        </p>

        {(status || added) && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {status ? (
              <span
                className={cn(
                  "text-[11px] font-medium",
                  status.tone === "warn" ? "text-amber-800 dark:text-amber-400" : "text-text-tertiary",
                )}
              >
                {status.label}
              </span>
            ) : null}
            {added ? (
              <span className="text-[11px] text-text-tertiary">{added}</span>
            ) : null}
          </div>
        )}
      </button>

      <div className="flex shrink-0 flex-col items-end gap-1.5 pt-0.5">
        {isPaper && (
          <span
            className="inline-flex items-center text-text-tertiary opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
            aria-hidden
          >
            <ArrowRight className="size-3.5" />
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
            {canPullRefMgr ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  void pullFromRefMgr();
                }}
                className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
                title={`Pull PDF from ${file.external_provider === "mendeley" ? "Mendeley" : "Zotero"}`}
              >
                <Upload className="size-3" /> Pull
              </button>
            ) : null}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
              className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
              title="Attach full text (PDF) to analyse"
            >
              <Upload className="size-3" /> Full text
            </button>
          </>
        )}

        <div className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
          {isPaper && (
            <IconBtn
              title="Ask Dhund"
              onClick={() => navigate(`/papers/${file.id}/chat`)}
            >
              <MessageSquare className="size-3.5" />
            </IconBtn>
          )}
          {isPaper && (
            <IconBtn
              title="Open in Research Intelligence"
              onClick={() => {
                try {
                  sessionStorage.setItem(
                    "dhund:compare-ids",
                    JSON.stringify([file.id]),
                  );
                } catch {
                  /* ignore */
                }
                navigate(`/research/compare?tab=compare&ids=${file.id}`);
              }}
            >
              <GitCompare className="size-3.5" />
            </IconBtn>
          )}
          {isPaper && (
            <IconBtn
              title="Add to collection"
              onClick={() => {
                window.dispatchEvent(
                  new CustomEvent("dhund:library-add-to-collection", {
                    detail: { fileIds: [file.id] },
                  }),
                );
              }}
            >
              <FolderPlus className="size-3.5" />
            </IconBtn>
          )}
          <IconBtn title="Delete" danger onClick={onDelete}>
            <Trash2 className="size-3.5" />
          </IconBtn>
        </div>
      </div>
    </div>
  );
}

function IconBtn({
  children,
  title,
  onClick,
  danger,
}: {
  children: React.ReactNode;
  title: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={cn(
        "rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground",
        danger && "hover:text-destructive",
      )}
    >
      {children}
    </button>
  );
}
