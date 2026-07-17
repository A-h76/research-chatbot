import { useState } from "react";
import { Search, Library, SlidersHorizontal, X } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { EmptyState } from "@/components/common/EmptyState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileCard } from "../components/FileCard";
import { useDeleteFile, useFiles, useLibraryStats, useLibraryTags } from "../useFiles";
import { useProjects } from "@/features/projects/useProjects";
import { useUI } from "@/context/UIContext";
import { toast } from "@/components/common/Toast";
import { cn } from "@/lib/utils";
import type { UserFile } from "@/types/api";

type SortKey    = "recent" | "title" | "authors" | "year" | "reading_status";
type StatusFilter = "all" | "unread" | "reading" | "read";

// ── Project scope banner ────────────────────────────────────────────────────
function ProjectScopeBanner() {
  const { currentProjectId, setCurrentProjectId } = useUI();
  const { data: projects = [] } = useProjects();

  if (!currentProjectId) return null;

  const proj = projects.find((p) => p.id === currentProjectId);
  if (!proj) return null;

  return (
    <div className="flex items-center gap-2 rounded-xl border border-primary/20 bg-accent-soft/60 px-4 py-2.5 text-sm">
      <span className="text-base leading-none">{proj.emoji}</span>
      <span className="font-medium">{proj.name}</span>
      <span className="text-muted-foreground">— showing papers in this project only</span>
      <button
        onClick={() => setCurrentProjectId(null)}
        className="ml-auto flex items-center gap-1 rounded-md px-2 py-0.5 text-xs text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
      >
        <X className="size-3" /> Show all
      </button>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────
export function FilesPage() {
  const { currentProjectId } = useUI();
  const { data: projects = [] } = useProjects();
  const { data: stats }         = useLibraryStats(currentProjectId);
  const { data: tagList = [] }  = useLibraryTags(currentProjectId);
  const deleteFile              = useDeleteFile();

  const [q,           setQ]           = useState("");
  const [status,      setStatus]      = useState<StatusFilter>("all");
  const [activeTags,  setActiveTags]  = useState<string[]>([]);
  const [sort,        setSort]        = useState<SortKey>("recent");
  const [showFilters, setShowFilters] = useState(false);
  const [toDelete,    setToDelete]    = useState<UserFile | null>(null);

  const params = {
    project_id:     currentProjectId,
    q:              q.trim() || undefined,
    reading_status: status !== "all" ? (status as "unread" | "reading" | "read") : undefined,
    tag:            activeTags.length ? activeTags : undefined,
    sort,
    kind:           "document" as const,
    limit:          200,
  };

  const { data: listData, isLoading } = useFiles(params);
  const files = listData?.items ?? [];

  function toggleTag(tag: string) {
    setActiveTags((prev) => prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]);
  }

  function clearFilters() {
    setQ(""); setStatus("all"); setActiveTags([]); setSort("recent");
  }

  const hasFilters = q || status !== "all" || activeTags.length > 0;

  const STATUS_TABS: { key: StatusFilter; label: string; count?: number }[] = [
    { key: "all",     label: "All",     count: stats?.total_papers },
    { key: "reading", label: "Reading", count: stats?.reading },
    { key: "unread",  label: "Unread",  count: stats?.unread },
    { key: "read",    label: "Read",    count: stats?.read },
  ];

  return (
    <PageContainer
      title="Knowledge Library"
      description="Your research papers, indexed and ready to analyse or chat with."
      actions={
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-1.5">
            <Search className="size-4 shrink-0 text-muted-foreground" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search title, author, tag…"
              className="w-40 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            {q && (
              <button onClick={() => setQ("")} className="text-muted-foreground hover:text-foreground">
                <X className="size-3.5" />
              </button>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className={cn(showFilters && "border-primary/50 bg-accent-soft text-primary")}
          >
            <SlidersHorizontal className="size-3.5" />
            Filters
          </Button>
        </div>
      }
    >
      <div className="space-y-5">

        {/* Project scope banner */}
        <ProjectScopeBanner />

        {/* Status tabs row */}
        <div className="flex items-center gap-1 border-b border-border pb-1">
          {STATUS_TABS.map(({ key, label, count }) => (
            <button
              key={key}
              onClick={() => setStatus(key)}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                status === key
                  ? "bg-accent-soft text-primary"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {label}
              {count !== undefined && (
                <span className={cn(
                  "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                  status === key ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground",
                )}>
                  {count}
                </span>
              )}
            </button>
          ))}

          {/* Sort */}
          <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
            <span className="hidden sm:inline">Sort:</span>
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

        {/* Expanded filter panel */}
        {showFilters && (
          <div className="rounded-xl border border-border bg-card p-4 space-y-3">
            {tagList.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-medium text-muted-foreground">Filter by tag</p>
                <div className="flex flex-wrap gap-2">
                  {tagList.map(({ tag, count }) => (
                    <button
                      key={tag}
                      onClick={() => toggleTag(tag)}
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs transition-colors",
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
                onClick={clearFilters}
                className="text-xs text-muted-foreground underline-offset-2 hover:underline"
              >
                Clear all filters
              </button>
            )}
          </div>
        )}

        {/* Active tag chips (collapsed filter panel) */}
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

        {/* Results */}
        {isLoading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-48 animate-pulse rounded-2xl bg-muted" />
            ))}
          </div>
        ) : files.length === 0 ? (
          hasFilters ? (
            <EmptyState
              title="No papers match your filters"
              description="Try clearing your filters or uploading more papers."
              action={<Button variant="outline" size="sm" onClick={clearFilters}>Clear filters</Button>}
            />
          ) : (
            <EmptyState
              icon={<Library className="size-8" />}
              title="Your library is empty"
              description="Attach a PDF or DOCX in any chat — it will be added here, indexed, and analysed automatically."
            />
          )
        ) : (
          <>
            <p className="text-xs text-muted-foreground">
              {listData?.total} paper{listData?.total !== 1 ? "s" : ""}
              {hasFilters ? " matching filters" : ""}
            </p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {files.map((f) => (
                <FileCard
                  key={f.id}
                  file={f}
                  project={projects.find((p) => p.id === f.project_id)}
                  onDelete={() => setToDelete(f)}
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
