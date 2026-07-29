import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, FileUp, Link2, X } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { EmptyState } from "@/components/common/EmptyState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileCard } from "../components/FileCard";
import { CollectionToolbar } from "../components/CollectionToolbar";
import { LibrarySearchFilters, type LibraryFilterState } from "../components/LibrarySearchFilters";
import { LibraryUploadZone } from "../components/LibraryUploadZone";
import { LibraryUploadQueue } from "../components/LibraryUploadQueue";
import { ConnectLibraryPanel } from "../components/ConnectLibraryPanel";
import { CollectionsPanel } from "../components/CollectionsPanel";
import { LibraryHealthStrip } from "../components/LibraryHealthStrip";
import { LibraryDuplicatesPanel } from "../components/LibraryDuplicatesPanel";
import { useLibraryUpload } from "../hooks/useLibraryUpload";
import { useDeleteFile, useFiles, useLibraryStats, useLibraryTags } from "../useFiles";
import { useLibraryFacets } from "../useLibraryFacets";
import { useProjects } from "@/features/projects/useProjects";
import { useQueryClient } from "@tanstack/react-query";
import { usePipelines } from "@/features/pipeline";
import { useUI } from "@/context/UIContext";
import { toast } from "@/components/common/Toast";
import { cn } from "@/lib/utils";
import type { LibraryListParams } from "../api";
import type { UserFile } from "@/types/api";
import { queryKeys } from "@/lib/queryKeys";
const PAGE_SIZE = 50;
type SortKey = NonNullable<LibraryListParams["sort"]>;
type StatusFilter = "all" | "unread" | "reading" | "read";
function readFiltersFromUrl(sp: URLSearchParams): LibraryFilterState {
  const tags = sp.getAll("tag").filter(Boolean);
  const recent = sp.get("recent_days");
  const src = sp.get("import_source");
  return {
    author: sp.get("author") || undefined,
    doi: sp.get("doi") || undefined,
    year: sp.get("year") || undefined,
    venue: sp.get("venue") || undefined,
    import_source: (src as LibraryFilterState["import_source"]) || undefined,
    recent_days: recent ? Number(recent) : undefined,
    tag: tags.length ? tags : undefined,
  };
}
function writeFiltersToUrl(sp: URLSearchParams, filters: LibraryFilterState) {
  sp.delete("author");
  sp.delete("doi");
  sp.delete("year");
  sp.delete("venue");
  sp.delete("import_source");
  sp.delete("recent_days");
  sp.delete("tag");
  if (filters.author) sp.set("author", filters.author);
  if (filters.doi) sp.set("doi", filters.doi);
  if (filters.year) sp.set("year", filters.year);
  if (filters.venue) sp.set("venue", filters.venue);
  if (filters.import_source) sp.set("import_source", filters.import_source);
  if (filters.recent_days) sp.set("recent_days", String(filters.recent_days));
  for (const t of filters.tag ?? []) sp.append("tag", t);
}
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
/** D5 — Dense Library (T1) + CollectionToolbar + Phase 1.5 search. */
export function FilesPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const { currentProjectId, setCurrentProjectId } = useUI();
  const { data: projects = [] } = useProjects();
  const { data: stats } = useLibraryStats(currentProjectId);
  const { data: tagList = [] } = useLibraryTags(currentProjectId);
  const { data: facets } = useLibraryFacets(currentProjectId);
  const deleteFile = useDeleteFile();
  const { items: uploadItems, isUploading, upload, clearFinished, recentUploaded } =
    useLibraryUpload();
  const [q, setQ] = useState(() => searchParams.get("q") ?? "");
  const [status, setStatus] = useState<StatusFilter>(
    () => (searchParams.get("reading_status") as StatusFilter) || "all",
  );
  const [filters, setFilters] = useState<LibraryFilterState>(() => readFiltersFromUrl(searchParams));
  const [sort, setSort] = useState<SortKey>(
    () => (searchParams.get("sort") as SortKey) || "recent",
  );
  const [page, setPage] = useState(() => {
    const off = Number(searchParams.get("offset") || 0);
    return Math.floor(off / PAGE_SIZE);
  });
  const [showFilters, setShowFilters] = useState(false);
  const [toDelete, setToDelete] = useState<UserFile | null>(null);
  const [collectionId, setCollectionId] = useState<number | null>(() => {
    const raw = searchParams.get("collection_id");
    return raw ? Number(raw) : null;
  });
  // Sync URL when search/filters change (debounced q)
  useEffect(() => {
    if (location.hash !== "#import") return;
    const el = document.getElementById("import");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [location.hash]);

  useEffect(() => {
    const t = window.setTimeout(() => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (q.trim()) next.set("q", q.trim());
        else next.delete("q");
        if (status !== "all") next.set("reading_status", status);
        else next.delete("reading_status");
        writeFiltersToUrl(next, filters);
        if (sort !== "recent") next.set("sort", sort);
        else next.delete("sort");
        if (collectionId != null) next.set("collection_id", String(collectionId));
        else next.delete("collection_id");
        const offset = page * PAGE_SIZE;
        if (offset > 0) next.set("offset", String(offset));
        else next.delete("offset");
        return next;
      }, { replace: true });
    }, 250);
    return () => window.clearTimeout(t);
  }, [q, status, filters, sort, page, collectionId, setSearchParams]);
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
  const params: LibraryListParams = {
    project_id: currentProjectId,
    q: q.trim() || undefined,
    reading_status: status !== "all" ? status : undefined,
    tag: filters.tag,
    author: filters.author,
    doi: filters.doi,
    year: filters.year,
    venue: filters.venue,
    import_source: filters.import_source,
    recent_days: filters.recent_days,
    collection_id: collectionId,
    sort,
    kind: "document",
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  };
  const { data: listData, isLoading } = useFiles(params);
  const files = listData?.items;
  const fileItems = files ?? [];
  const total = listData?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const paperIds = useMemo(
    () => (files ?? []).filter((f) => f.kind === "document").map((f) => f.id),
    [files],
  );
  const metaById = useMemo(() => {
    const m: Record<number, string> = {};
    for (const f of files ?? []) m[f.id] = f.meta_status;
    return m;
  }, [files]);
  const { byId: pipelineById } = usePipelines(paperIds, metaById);
  function patchFilters(patch: Partial<LibraryFilterState>) {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(0);
  }
  function clearFilters() {
    setQ("");
    setStatus("all");
    setFilters({});
    setSort("recent");
    setCollectionId(null);
    setPage(0);
  }
  const hasFilters = Boolean(
    q ||
      status !== "all" ||
      collectionId != null ||
      filters.author ||
      filters.doi ||
      filters.year ||
      filters.venue ||
      filters.import_source ||
      filters.recent_days ||
      (filters.tag?.length ?? 0) > 0,
  );
  const hasLibrary = (stats?.total_papers ?? 0) > 0 || total > 0;
  const STATUS_TABS: { key: StatusFilter; label: string; count?: number }[] = [
    { key: "all", label: "All", count: facets?.total ?? stats?.total_papers },
    { key: "reading", label: "Reading", count: facets?.reading_status?.reading ?? stats?.reading },
    { key: "unread", label: "Unread", count: facets?.reading_status?.unread ?? stats?.unread },
    { key: "read", label: "Read", count: facets?.reading_status?.read ?? stats?.read },
  ];
  const recentSession = recentUploaded.slice(0, 8);
  const rangeStart = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const rangeEnd = Math.min((page + 1) * PAGE_SIZE, total);
  return (
    <PageContainer title="Library" description="Search and filter your research papers.">
      <div className="space-y-4">
        <CollectionToolbar
          q={q}
          onQChange={(v) => {
            setQ(v);
            setPage(0);
          }}
          showFilters={showFilters}
          onToggleFilters={() => setShowFilters((v) => !v)}
          isUploading={isUploading}
        />
        <ProjectScopeBanner />
        <ConnectLibraryPanel
          projectId={currentProjectId}
          onImported={(pid) => {
            void queryClient.invalidateQueries({ queryKey: queryKeys.files });
            void queryClient.invalidateQueries({ queryKey: ["library"] });
            void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
            void queryClient.invalidateQueries({ queryKey: ["library", "collections"] });
            if (pid) setCurrentProjectId(pid);
          }}
        />
        <LibraryHealthStrip projectId={currentProjectId} />
        <LibraryDuplicatesPanel projectId={currentProjectId} />
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          <CollectionsPanel
            activeId={collectionId}
            onSelect={(id) => {
              setCollectionId(id);
              setPage(0);
            }}
          />
          <div className="min-w-0 flex-1 space-y-4">
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
              onClick={() => {
                setStatus(key);
                setPage(0);
              }}
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
              <option value="recent">Recently added</option>
              <option value="title">Title</option>
              <option value="authors">Author</option>
              <option value="year">Year</option>
              <option value="reading_status">Reading status</option>
            </select>
          </div>
        </div>
        {showFilters && (
          <LibrarySearchFilters
            filters={filters}
            onChange={patchFilters}
            facets={facets}
            tagList={tagList}
            onClear={clearFilters}
          />
        )}
        {(filters.tag?.length ?? 0) > 0 && !showFilters && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted-foreground">Tags:</span>
            {filters.tag!.map((t) => (
              <Badge
                key={t}
                variant="secondary"
                className="cursor-pointer gap-1 text-xs"
                onClick={() =>
                  patchFilters({
                    tag: filters.tag!.filter((x) => x !== t).length
                      ? filters.tag!.filter((x) => x !== t)
                      : undefined,
                  })
                }
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
        ) : fileItems.length === 0 ? (
          hasFilters ? (
            <EmptyState
              title="No papers match your search"
              description="Try different keywords or clear filters."
              action={
                <Button variant="outline" size="sm" onClick={clearFilters}>
                  Clear filters
                </Button>
              }
            />
          ) : (
            <div className="px-2 py-14 text-center sm:py-16">
              <p className="text-[22px] font-semibold tracking-tight text-foreground">
                Start your research
              </p>
              <p className="mx-auto mt-2 max-w-md text-[14px] leading-relaxed text-muted-foreground">
                Import papers into Dhund, attach PDFs, and wait until they become Research Ready —
                then write from evidence.
              </p>
              <div className="mx-auto mt-8 flex max-w-md flex-col gap-3 sm:flex-row sm:justify-center">
                <Button
                  type="button"
                  className="gap-2"
                  onClick={() => {
                    document.getElementById("import")?.scrollIntoView({
                      behavior: "smooth",
                      block: "start",
                    });
                  }}
                >
                  <FileUp className="size-4" />
                  Upload PDF
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="gap-2"
                  onClick={() => {
                    document.getElementById("import")?.scrollIntoView({
                      behavior: "smooth",
                      block: "start",
                    });
                  }}
                >
                  <Link2 className="size-4" />
                  Zotero / Mendeley
                </Button>
              </div>
              <p className="mt-5 text-[12px] text-muted-foreground">
                Or import BibTeX / RIS from the Import research panel above.
              </p>
            </div>
          )
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-[12px] text-muted-foreground tabular-nums">
                Showing {rangeStart}–{rangeEnd} of {total.toLocaleString()} paper
                {total !== 1 ? "s" : ""}
                {hasFilters ? " matching" : ""}
              </p>
              {totalPages > 1 && (
                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 px-2"
                    disabled={page <= 0}
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                  >
                    <ChevronLeft className="size-4" />
                  </Button>
                  <span className="px-2 text-xs tabular-nums text-muted-foreground">
                    Page {page + 1} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 px-2"
                    disabled={page >= totalPages - 1}
                    onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  >
                    <ChevronRight className="size-4" />
                  </Button>
                </div>
              )}
            </div>
            <div className="overflow-hidden rounded-lg border border-border bg-card">
              {fileItems.map((f) => (
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
        </div>
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
