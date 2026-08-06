import { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FileText, Library } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { LibraryUploadZone } from "@/features/files/components/LibraryUploadZone";
import { LibraryUploadQueue } from "@/features/files/components/LibraryUploadQueue";
import { useProjectUpload } from "@/features/files/hooks/useProjectUpload";
import { useFiles } from "@/features/files/useFiles";
import { AiStateBadge, usePipelines, type AiStateResolved } from "@/features/pipeline";
import { useUI } from "@/context/UIContext";
import { cn } from "@/lib/utils";
import type { UserFile } from "@/types/api";

const RS_ICON = {
  read: "text-emerald-600 dark:text-emerald-400",
  reading: "text-amber-600 dark:text-amber-400",
  unread: "text-muted-foreground",
} as const;

function PaperListRow({
  file,
  onClick,
  aiState,
}: {
  file: UserFile;
  onClick: () => void;
  aiState?: AiStateResolved;
}) {
  const title = file.title || file.name;
  const rs = file.reading_status ?? "unread";
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full items-center gap-2.5 rounded-md border border-border px-3 py-2 text-left transition-colors hover:bg-muted/40"
    >
      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft">
        <FileText className="size-4 text-primary" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{title}</p>
        <p className="truncate text-xs text-muted-foreground">
          {[file.authors?.split(";")[0]?.trim(), file.year].filter(Boolean).join(" · ") ||
            file.name}
        </p>
      </div>
      <AiStateBadge state={aiState} metaStatus={file.meta_status} />
      <span className={cn("text-[10px] capitalize", RS_ICON[rs])}>{rs}</span>
    </button>
  );
}

/** Lazy-loaded full paper list for a project workspace. */
export function ProjectPapersPanel({ projectId }: { projectId: number }) {
  const navigate = useNavigate();
  const { setCurrentProjectId } = useUI();
  const { data, isLoading } = useFiles({
    project_id: projectId,
    kind: "document",
    limit: 500,
    sort: "recent",
  });

  function openPaper(fileId: number) {
    setCurrentProjectId(projectId);
    navigate(`/papers/${fileId}`);
  }

  function openLibrary() {
    setCurrentProjectId(projectId);
    navigate("/library");
  }
  const papers = data?.items;
  const paperItems = papers ?? [];
  const paperIds = useMemo(() => (papers ?? []).map((f) => f.id), [papers]);
  const metaById = useMemo(() => {
    const m: Record<number, string> = {};
    for (const f of papers ?? []) m[f.id] = f.meta_status;
    return m;
  }, [papers]);
  const { byId: pipelineById } = usePipelines(paperIds, metaById);
  const { items: uploadItems, isUploading, upload, clearFinished } = useProjectUpload(projectId);
  const uploaded = uploadItems.filter((i) => i.status === "uploaded" && i.fileId != null);
  const inFlight = uploadItems.filter((i) => i.status === "uploading" || i.status === "queued");
  const showNext = uploaded.length > 0 && inFlight.length === 0;
  const firstId = uploaded[0]?.fileId ?? null;

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-20 w-full rounded-xl" />
        <Skeleton className="h-14 w-full rounded-xl" />
        <Skeleton className="h-14 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">Papers ({data?.total ?? paperItems.length})</h2>
          <p className="text-xs text-muted-foreground">
            Upload here or assign papers from the library.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5 shrink-0"
          onClick={openLibrary}
        >
          <Library className="size-3.5" /> Library
        </Button>
      </div>

      <LibraryUploadZone
        compact={paperItems.length > 0}
        disabled={isUploading}
        onFiles={(f) => void upload(f)}
        inputId={`project-${projectId}-upload`}
      />
      <LibraryUploadQueue items={uploadItems} onClearFinished={clearFinished} />

      {showNext && (
        <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-2">
          <p className="text-sm font-medium">
            {uploaded.length} paper{uploaded.length === 1 ? "" : "s"} in this project
          </p>
          <p className="text-xs text-muted-foreground">
            Processing continues in the background. Open a paper to watch status, then ask Dhund or
            extract Evidence.
          </p>
          <div className="flex flex-wrap gap-2">
            {firstId != null && (
              <Button asChild size="sm">
                <Link
                  to={`/papers/${firstId}`}
                  onClick={() => setCurrentProjectId(projectId)}
                >
                  Open first paper
                </Link>
              </Button>
            )}
            <Button size="sm" variant="ghost" onClick={clearFinished}>
              Dismiss
            </Button>
          </div>
        </div>
      )}

      {paperItems.length === 0 ? (
        <div className="dhund-enter rounded-xl border border-dashed border-border px-6 py-10 text-center">
          <p className="text-sm font-medium text-foreground">No papers in this project yet</p>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Upload PDFs above, or assign existing library papers so chat and writing stay scoped
            here.
          </p>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
            <Button size="sm" variant="outline" className="gap-1.5" onClick={openLibrary}>
              <Library className="size-3.5" /> Browse library
            </Button>
          </div>
          <p className="mt-3 text-[11px] text-muted-foreground">
            Next · Drop files on the upload zone — processing continues in the background.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {paperItems.map((f) => (
            <PaperListRow
              key={f.id}
              file={f}
              aiState={pipelineById.get(f.id)?.aiState}
              onClick={() => openPaper(f.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
