import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Trash2,
  Upload,
  MessageSquare,
  GitCompare,
  FolderPlus,
  ExternalLink,
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

type IntelChip = { id: string; label: string; on?: boolean };

function intelligenceChips(
  file: UserFile,
  aiState?: AiStateResolved,
): IntelChip[] {
  const r = file.research_readiness;
  const aid = aiState?.id;
  const chatReady = r === "research_ready" || aid === "chat_ready";
  const profile =
    r === "analysed" ||
    r === "indexed" ||
    r === "research_ready" ||
    (file.meta_status === "done" && r !== "metadata_only" && r !== "pdf_attached");
  const evidence =
    r === "indexed" ||
    r === "research_ready" ||
    aid === "evidence_ready" ||
    aid === "graph_ready" ||
    aid === "chat_ready";
  const graph =
    aid === "graph_ready" || aid === "chat_ready" || r === "research_ready";

  return [
    { id: "chat", label: "Chat Ready", on: chatReady },
    { id: "profile", label: "Research Profile", on: profile },
    { id: "evidence", label: "Evidence", on: evidence },
    { id: "graph", label: "Knowledge Graph", on: graph },
  ];
}

/**
 * Dense Library row — corpus intelligence, not a document card.
 */
export function FileCard({
  file,
  project,
  onDelete,
  aiState,
  selected = false,
  onToggleSelect,
}: {
  file: UserFile;
  project?: Project;
  onDelete: () => void;
  aiState?: AiStateResolved;
  selected?: boolean;
  onToggleSelect?: (id: number) => void;
}) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const rs = (file.reading_status ?? "unread") as "unread" | "reading" | "read";
  const isPaper = file.kind === "document";
  const readiness = file.research_readiness;
  const metadataOnly =
    isPaper &&
    (readiness === "metadata_only" ||
      file.has_pdf === false ||
      (!readiness && (file.size === 0 || !file.size)));
  const displayTitle = file.title || file.name;
  const authors = file.authors?.split(";")[0]?.trim();
  const meta = [authors, file.year].filter(Boolean).join(" · ");
  const study = studyTypeLabel(file);
  const chips = isPaper ? intelligenceChips(file, aiState) : [];

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
        "group relative flex w-full items-start gap-2.5 border-b border-border px-1 py-2.5 text-left transition-colors last:border-b-0",
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
          className="truncate text-[13px] font-medium leading-snug text-foreground"
          title={displayTitle}
        >
          {displayTitle}
        </p>
        <p className="mt-0.5 truncate text-[12px] text-muted-foreground">
          {meta || (file.title && file.title !== file.name ? file.name : "No metadata yet")}
          {study ? (
            <span className="text-muted-foreground/90"> · {study}</span>
          ) : null}
          {project ? (
            <span className="text-muted-foreground/80">
              {" "}
              · {project.emoji} {project.name}
            </span>
          ) : null}
        </p>

        {chips.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {chips.map((c) => (
              <span
                key={c.id}
                className={cn(
                  "rounded border px-1.5 py-px text-[10px] font-medium tracking-wide",
                  c.on
                    ? "border-primary/30 bg-primary/8 text-primary"
                    : "border-border text-muted-foreground/70",
                )}
              >
                {c.label}
              </span>
            ))}
          </div>
        )}
      </button>

      <div className="flex shrink-0 flex-col items-end gap-1.5 pt-0.5">
        <span
          className={cn(
            "text-[11px] capitalize tabular-nums",
            rs === "unread" && "font-medium text-foreground",
            rs === "reading" && "font-medium text-sem-warn",
            rs === "read" && "text-muted-foreground",
          )}
        >
          {rs}
        </span>

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

        {/* Hover actions */}
        <div className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
          <IconBtn title="Open" onClick={open}>
            <ExternalLink className="size-3.5" />
          </IconBtn>
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
              title="Compare"
              onClick={() => {
                try {
                  sessionStorage.setItem(
                    "dhund:compare-ids",
                    JSON.stringify([file.id]),
                  );
                } catch {
                  /* ignore */
                }
                navigate(`/research/compare?tab=matrix&ids=${file.id}`);
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
