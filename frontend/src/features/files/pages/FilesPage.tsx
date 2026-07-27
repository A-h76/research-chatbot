import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Library, X } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { EmptyState } from "@/components/common/EmptyState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileCard } from "../components/FileCard";
import { CollectionToolbar } from "../components/CollectionToolbar";
import { LibraryUploadZone } from "../components/LibraryUploadZone";
import { LibraryUploadQueue } from "../components/LibraryUploadQueue";
import { useLibraryUpload } from "../hooks/useLibraryUpload";
import { useDeleteFile, useFiles, useLibraryStats, useLibraryTags } from "../useFiles";
import { useProjects } from "@/features/projects/useProjects";
import { usePipelines } from "@/features/pipeline";
import { useUI } from "@/context/UIContext";
import { toast } from "@/components/common/Toast";
import { cn } from "@/lib/utils";
import type { UserFile } from "@/types/api";

type SortKey = "recent" | "title" | "authors" | "year" | "reading_status";
type StatusFilter = "all" | "unread" | "reading" | "read";

function ProjectScopeBanner() {
  const { currentProjectId, setCurrentProjectId } = useUI();
  const { data: projects = [] } = useProjects();

  if (!currentProjectId) return null;

  const proj = projects.find((p) => p.id === currentProjectId);
  if (!proj) return null;

  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-[13px]">
      <span className="text-base leading-none">{proj.emoji}</span>
      <span className="font-medium">{proj.name}</span>
      <span className="text-muted-foreground">— this project only</span>
      <button
        type="button"
        onClick={() => setCurrentProjectId(null)}
        className="ml-auto flex items-center gap-1 rounded-md px-2 py-0.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
      >
        <X className="size-3" /> Show all
      </button>
    </div>
  );
}

/** D5 — Dense Library (T1) + CollectionToolbar. */
export function FilesPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { currentProjectId } = useUI();
  const { data: projects = [] } = useProjects();
  const { data: stats } = useLibraryStats(currentProjectId);
  const { data: tagList = [] } = useLibraryTags(currentProjectId);
  const deleteFile = useDeleteFile();
  const { items: uploadItems, isUploading, upload, clearFinished, recentUploaded } =
    useLibraryUpload();

  const [q, setQ] = useState(() => searchParams.get("q") ?? "");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [activeTags, setActiveTags] = useState<string[]>([]);
  const [sort, setSort] = useState<SortKey>("recent");
  const [showFilters, setShowFilters] = useState(false);
  const [toDelete, setToDelete] = useState<UserFile | null>(null);

  // D8 — ⌘K “Find in library” / “Upload paper”
  useEffect(() => {
    const qParam = searchParams.get("q");
    if (qParam != null) setQ(qParam);
  }, [searchParams]);

  useEffect(() => {
    if (searchParams.get("upload") !== "1") return;
    const t = window.setTimeout(() => {
      document.getElementById("library-upload-input")?.click();
    }, 80);
    const next = new URLSearchParams(searchParams);
    next.delete("upload");
    setSearchParams(next, { replace: true });
    return () => window.clearTimeout(t);
  }, [searchParams, setSearchParams]);

  const params = {
    project_id: currentProjectId,
    q: q.trim() || undefined,
    reading_status: status !== "all" ? (status as "unread" | "reading" | "read") : undefined,
    tag: activeTags.length ? activeTags : undefined,
    sort,
    kind: "document" as const,
    limit: 200,
  };

  const { data: listData, isLoading } = useFiles(params);
  const files = listData?.items ?? [];

  const paperIds = useMemo(
    () => files.filter((f) => f.kind === "document").map((f) => f.id),
    [files],
  );
  const metaById = useMemo(() => {
    const m: Record<number, string> = {};
    for (const f of files) m[f.id] = f.meta_status;
    return m;
  }, [files]);
  const { byId: pipelineById } = usePipelines(paperIds, metaById);

  function toggleTag(tag: string) {
    setActiveTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  }

  function clearFilters() {
    setQ("");
    setStatus("all");
    setActiveTags([]);
    setSort("recent");
  }

  const hasFilters = Boolean(q || status !== "all" || activeTags.length > 0);
  const hasLibrary = (stats?.total_papers ?? 0) > 0 || files.length > 0;

  const STATUS_TABS: { key: StatusFilter; label: string; count?: number }[] = [
    { key: "all", label: "All", count: stats?.total_papers },
    { key: "reading", label: "Reading", count: stats?.reading },
    { key: "unread", label: "Unread", count: stats?.unread },
    { key: "read", label: "Read", count: stats?.read },
  ];

  const recentSession = recentUploaded.slice(0, 8);

  return (
    <PageContainer title="Library" description="Papers ready to analyse, compare, and cite.">
      <div className="space-y-4">
        <CollectionToolbar
          q={q}
          onQChange={setQ}
          showFilters={showFilters}
          onToggleFilters={() => setShowFilters((v) => !v)}
          isUploading={isUploading}
        />

        <ProjectScopeBanner />

        <LibraryUploadZone
          disabled={isUploading}
          onFiles={(f) => void upload(f)}
          compact={hasLibrary}
        />
        <LibraryUploadQueue items={uploadItems} onClearFinished={clearFinished} />

        {recentSession.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {recentSession.map((item) => (
              <Badge
                key={item.key}
                variant="secondary"
                className={cn(
                  "max-w-[200px] truncate font-normal",
                  item.fileId != null && "cursor-pointer hover:bg-accent-soft",
                )}
                title={item.filename}
                onClick={() => {
                  if (item.fileId != null) navigate(`/papers/${item.fileId}`);
                }}
              >
                {item.filename}
              </Badge>
            ))}
          </div>
        )}

        <div className="flex items-center gap-1 border-b border-border pb-1">
          {STATUS_TABS.map(({ key, label, count }) => (
            <button
              key={key}
              type="button"
              onClick={() => setStatus(key)}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[13px] font-medium transition-colors",
                status === key
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
              {count !== undefined && (
                <span
                  className={cn(
                    "rounded px-1.5 py-0.5 text-[10px] font-semibold tabular-nums",
                    status === key ? "bg-background text-foreground" : "bg-muted text-muted-foreground",
                  )}
                >
                  {count}
                </span>
              )}
            </button>
          ))}

          <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
            <span className="hidden sm:inline">Sort</span>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
              className="rounded border border-border bg-transparent px-2 py-1 text-xs outline-none"
            >
              <option value="recent">Recent</option>
              <option value="title">Title</option>
              <option value="authors">Authors</option>
              <option value="year">Year</option>
              <option value="reading_status">Status</option>
            </select>
          </div>
        </div>

        {showFilters && (
          <div className="rounded-lg border border-border bg-card p-3 space-y-3">
            {tagList.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-medium text-muted-foreground">Tags</p>
                <div className="flex flex-wrap gap-1.5">
                  {tagList.map(({ tag, count }) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => toggleTag(tag)}
                      className={cn(
                        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs transition-colors",
                        activeTags.includes(tag)
                          ? "border-primary bg-accent-soft text-primary"
                          : "border-border text-muted-foreground hover:border-primary/40 hover:text-foreground",
                      )}
                    >
                      {tag}
                      <span className="text-[10px] opacity-70">{count}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {hasFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="text-xs text-muted-foreground underline-offset-2 hover:underline"
              >
                Clear all filters
              </button>
            )}
          </div>
        )}

        {activeTags.length > 0 && !showFilters && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">Tags:</span>
            {activeTags.map((t) => (
              <Badge
                key={t}
                variant="secondary"
                className="cursor-pointer gap-1 text-xs"
                onClick={() => toggleTag(t)}
              >
                {t} <X className="size-2.5" />
              </Badge>
            ))}
          </div>
        )}

        {isLoading ? (
          <div className="space-y-0 rounded-lg border border-border bg-card divide-y divide-border overflow-hidden">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-12 animate-pulse bg-muted/40" />
            ))}
          </div>
        ) : files.length === 0 ? (
          hasFilters ? (
            <EmptyState
              title="No papers match your filters"
              description="Try clearing filters or uploading more papers."
              action={
                <Button variant="outline" size="sm" onClick={clearFilters}>
                  Clear filters
                </Button>
              }
            />
          ) : (
            <EmptyState
              icon={<Library className="size-8" />}
              title="Your library is empty"
              description="Upload a PDF from the toolbar — no need to open Chat first."
            />
          )
        ) : (
          <>
            <p className="text-[12px] text-muted-foreground">
              {listData?.total} paper{listData?.total !== 1 ? "s" : ""}
              {hasFilters ? " matching" : ""}
            </p>
            <div className="overflow-hidden rounded-lg border border-border bg-card">
              {files.map((f) => (
                <FileCard
                  key={f.id}
                  file={f}
                  project={projects.find((p) => p.id === f.project_id)}
                  onDelete={() => setToDelete(f)}
                  aiState={pipelineById.get(f.id)?.aiState}
                />
              ))}
            </div>
          </>
        )}
      </div>

      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        title="Delete this paper?"
        description="It will be removed from your library and can no longer be retrieved."
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          if (toDelete) {
            deleteFile.mutate(toDelete.id);
            toast.success("Paper deleted");
          }
        }}
      />
    </PageContainer>
  );
}
