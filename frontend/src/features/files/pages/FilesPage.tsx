import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { EmptyState } from "@/components/common/EmptyState";
import { LibraryPapersSkeleton } from "@/components/common/ResearchSkeletons";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { FileCard } from "../components/FileCard";
import { CollectionToolbar } from "../components/CollectionToolbar";
import { LibrarySearchFilters, type LibraryFilterState } from "../components/LibrarySearchFilters";
import { LibraryUploadQueue } from "../components/LibraryUploadQueue";
import {
  ConnectLibraryPanel,
  type ConnectLibraryPanelHandle,
} from "../components/ConnectLibraryPanel";
import { CollectionsPanel } from "../components/CollectionsPanel";
import { LibraryHealthStrip } from "../components/LibraryHealthStrip";
import { LibraryDuplicatesPanel } from "../components/LibraryDuplicatesPanel";
import { UploadPapersDialog } from "../components/UploadPapersDialog";
import { LibraryImportMenu } from "../components/LibraryImportMenu";
import { useLibraryUpload } from "../hooks/useLibraryUpload";
import { useLibraryCollections } from "../hooks/useLibraryCollections";
import { useDeleteFile, useFiles, useLibraryStats, useLibraryTags } from "../useFiles";
import { useLibraryFacets } from "../useLibraryFacets";
import { libraryBridgeApi } from "../libraryBridgeApi";
import { collectionsApi } from "../collectionsApi";
import { useProjects } from "@/features/projects/useProjects";
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
    <div className="flex items-center gap-2 py-1 text-[13px]">
      <span className="text-base leading-none">{proj.emoji}</span>
      <span className="font-medium">{proj.name}</span>
      <span className="text-muted-foreground">— this project only</span>
      <button
        type="button"
        onClick={() => setCurrentProjectId(null)}
        className="ml-auto flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        <X className="size-3" /> Show all
      </button>
    </div>
  );
}

/** Library — research corpus home (Places IA preserved). */
export function FilesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const { currentProjectId, setCurrentProjectId } = useUI();
  const { data: projects = [] } = useProjects();
  const { data: stats } = useLibraryStats(currentProjectId);
  const { data: tagList = [] } = useLibraryTags(currentProjectId);
  const { data: facets } = useLibraryFacets(currentProjectId);
  const { data: collections = [] } = useLibraryCollections();
  const { data: health } = useQuery({
    queryKey: ["library", "health", currentProjectId ?? null],
    queryFn: () => libraryBridgeApi.health(currentProjectId),
  });
  const deleteFile = useDeleteFile();
  const { items: uploadItems, isUploading, upload, clearFinished, recentUploaded } =
    useLibraryUpload();
  const sourcesRef = useRef<ConnectLibraryPanelHandle>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
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
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [addToCollectionIds, setAddToCollectionIds] = useState<number[] | null>(null);
  const [pickCollectionId, setPickCollectionId] = useState<number | "">("");

  useEffect(() => {
    const t = window.setTimeout(() => {
      setSearchParams(
        (prev) => {
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
          const provider = prev.get("provider");
          if (provider) next.set("provider", provider);
          return next;
        },
        { replace: true },
      );
    }, 250);
    return () => window.clearTimeout(t);
  }, [q, status, filters, sort, page, collectionId, setSearchParams]);

  useEffect(() => {
    const provider = searchParams.get("provider");
    if (provider === "upload" || searchParams.get("upload") === "1") {
      setUploadOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete("upload");
      if (provider === "upload") next.delete("provider");
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    const onAdd = (e: Event) => {
      const detail = (e as CustomEvent<{ fileIds: number[] }>).detail;
      if (detail?.fileIds?.length) setAddToCollectionIds(detail.fileIds);
    };
    window.addEventListener("dhund:library-add-to-collection", onAdd);
    return () => window.removeEventListener("dhund:library-add-to-collection", onAdd);
  }, []);

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
  const paperCount = stats?.total_papers ?? total;
  const collectionCount = collections.length;
  const readyCount = health?.research_ready;

  const STATUS_TABS: { key: StatusFilter; label: string; count?: number }[] = [
    { key: "all", label: "All", count: facets?.total ?? stats?.total_papers },
    { key: "unread", label: "Unread", count: facets?.reading_status?.unread ?? stats?.unread },
    { key: "reading", label: "Reading", count: facets?.reading_status?.reading ?? stats?.reading },
    { key: "read", label: "Read", count: facets?.reading_status?.read ?? stats?.read },
  ];
  const recentSession = recentUploaded.slice(0, 8);
  const rangeStart = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const rangeEnd = Math.min((page + 1) * PAGE_SIZE, total);

  const statsLine = hasLibrary
    ? [
        `${paperCount.toLocaleString()} paper${paperCount === 1 ? "" : "s"}`,
        collectionCount > 0
          ? `${collectionCount} collection${collectionCount === 1 ? "" : "s"}`
          : null,
        readyCount != null && readyCount > 0
          ? `${readyCount} chat-ready`
          : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : "Your research corpus";

  function onImported(pid?: number | null) {
    void queryClient.invalidateQueries({ queryKey: queryKeys.files });
    void queryClient.invalidateQueries({ queryKey: ["library"] });
    void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    void queryClient.invalidateQueries({ queryKey: ["library", "collections"] });
    if (pid) setCurrentProjectId(pid);
  }

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const selectedList = Array.from(selectedIds);

  async function confirmAddToCollection() {
    if (!addToCollectionIds?.length || pickCollectionId === "") return;
    try {
      const res = await collectionsApi.addPapers(
        Number(pickCollectionId),
        addToCollectionIds,
      );
      toast.success(
        res.added
          ? `Added ${res.added} paper${res.added === 1 ? "" : "s"} to collection`
          : "Already in that collection",
      );
      void queryClient.invalidateQueries({ queryKey: ["library", "collections"] });
      setAddToCollectionIds(null);
      setPickCollectionId("");
      setSelectedIds(new Set());
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not add to collection");
    }
  }

  return (
    <PageContainer description={statsLine} dense maxWidth="6xl">
      <div className="space-y-6">
        {hasLibrary && (
          <CollectionToolbar
            q={q}
            onQChange={(v) => {
              setQ(v);
              setPage(0);
            }}
            showFilters={showFilters}
            onToggleFilters={() => setShowFilters((v) => !v)}
            isUploading={isUploading}
            onUpload={() => setUploadOpen(true)}
            onBibtex={() => sourcesRef.current?.openBibtex()}
            onZoteroImport={() => sourcesRef.current?.openZoteroImport()}
            onMendeleyImport={() => sourcesRef.current?.openMendeleyImport()}
            selectedCount={selectedIds.size}
            onClearSelection={() => setSelectedIds(new Set())}
            onBulkAsk={() => {
              const first = selectedList[0];
              if (first) navigate(`/papers/${first}/chat`);
              else navigate("/chat");
            }}
            onBulkCompare={() => {
              if (selectedList.length < 2) return;
              try {
                sessionStorage.setItem(
                  "dhund:compare-ids",
                  JSON.stringify(selectedList),
                );
              } catch {
                /* ignore */
              }
              navigate(
                `/research/compare?tab=compare&ids=${selectedList.join(",")}`,
              );
            }}
            onBulkAddToCollection={() => setAddToCollectionIds(selectedList)}
          />
        )}
        <ProjectScopeBanner />
        <ConnectLibraryPanel
          ref={sourcesRef}
          projectId={currentProjectId}
          onImported={onImported}
        />

        {hasLibrary && (
          <>
            <LibraryHealthStrip
              projectId={currentProjectId}
              unreadCount={facets?.reading_status?.unread ?? stats?.unread}
              onFilterNeedsReview={() => {
                setStatus("unread");
                setPage(0);
              }}
            />
            <LibraryDuplicatesPanel projectId={currentProjectId} />
          </>
        )}

        {!hasLibrary && !isLoading ? (
          <div className="mx-auto max-w-md py-16 text-center">
            <p className="text-[18px] font-semibold tracking-tight text-foreground">
              Your research library is empty
            </p>
            <p className="mt-2 text-[14px] leading-relaxed text-muted-foreground">
              Upload PDFs to build the corpus your research sessions draw from.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
              <Button disabled={isUploading} onClick={() => setUploadOpen(true)}>
                Upload papers
              </Button>
              <LibraryImportMenu
                onUpload={() => setUploadOpen(true)}
                onBibtex={() => sourcesRef.current?.openBibtex()}
                onZoteroImport={() => sourcesRef.current?.openZoteroImport()}
                onMendeleyImport={() => sourcesRef.current?.openMendeleyImport()}
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-8 sm:flex-row sm:items-start">
            <CollectionsPanel
              activeId={collectionId}
              totalPapers={paperCount}
              onSelect={(id) => {
                setCollectionId(id);
                setPage(0);
                setSelectedIds(new Set());
              }}
            />
            <div className="min-w-0 flex-1 space-y-4">
              {uploadItems.length > 0 && (
                <LibraryUploadQueue items={uploadItems} onClearFinished={clearFinished} />
              )}
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

              <div className="flex items-center gap-1 border-b border-border/70">
                {STATUS_TABS.map(({ key, label, count }) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => {
                      setStatus(key);
                      setPage(0);
                    }}
                    className={cn(
                      "relative flex items-center gap-1.5 px-2.5 py-2 text-[13px] font-medium transition-colors",
                      status === key
                        ? "text-foreground after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:rounded-full after:bg-primary"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {label}
                    {count !== undefined && (
                      <span className="tabular-nums text-[11px] text-muted-foreground">
                        {count}
                      </span>
                    )}
                  </button>
                ))}
                <div className="ml-auto flex items-center gap-2 pb-1 text-xs text-muted-foreground">
                  <select
                    value={sort}
                    onChange={(e) => setSort(e.target.value as SortKey)}
                    className="bg-transparent py-1 text-xs outline-none"
                    aria-label="Sort papers"
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
                <LibraryPapersSkeleton />
              ) : fileItems.length === 0 ? (
                <EmptyState
                  title="No papers match"
                  description="Try different keywords or clear filters."
                  action={
                    <Button variant="outline" size="sm" onClick={clearFilters}>
                      Clear filters
                    </Button>
                  }
                />
              ) : (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-[12px] text-muted-foreground tabular-nums">
                      {rangeStart}–{rangeEnd} of {total.toLocaleString()}
                      {hasFilters ? " matching" : ""}
                    </p>
                    {totalPages > 1 && (
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2"
                          disabled={page <= 0}
                          onClick={() => setPage((p) => Math.max(0, p - 1))}
                        >
                          <ChevronLeft className="size-4" />
                        </Button>
                        <span className="px-2 text-xs tabular-nums text-muted-foreground">
                          {page + 1} / {totalPages}
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2"
                          disabled={page >= totalPages - 1}
                          onClick={() =>
                            setPage((p) => Math.min(totalPages - 1, p + 1))
                          }
                        >
                          <ChevronRight className="size-4" />
                        </Button>
                      </div>
                    )}
                  </div>
                  <div>
                    {fileItems.map((f) => (
                      <FileCard
                        key={f.id}
                        file={f}
                        project={projects.find((p) => p.id === f.project_id)}
                        onDelete={() => setToDelete(f)}
                        aiState={pipelineById.get(f.id)?.aiState}
                        selected={selectedIds.has(f.id)}
                        onToggleSelect={toggleSelect}
                      />
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      <UploadPapersDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        disabled={isUploading}
        onFiles={(f) => void upload(f)}
        uploadItems={uploadItems}
        onClearFinished={clearFinished}
      />

      <Dialog
        open={addToCollectionIds != null}
        onOpenChange={(o) => {
          if (!o) {
            setAddToCollectionIds(null);
            setPickCollectionId("");
          }
        }}
      >
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Add to collection</DialogTitle>
          </DialogHeader>
          {collections.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Create a collection in the sidebar first.
            </p>
          ) : (
            <select
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              value={pickCollectionId === "" ? "" : String(pickCollectionId)}
              onChange={(e) =>
                setPickCollectionId(e.target.value ? Number(e.target.value) : "")
              }
            >
              <option value="">Choose collection…</option>
              {collections.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.paper_count})
                </option>
              ))}
            </select>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setAddToCollectionIds(null);
                setPickCollectionId("");
              }}
            >
              Cancel
            </Button>
            <Button
              disabled={pickCollectionId === "" || !addToCollectionIds?.length}
              onClick={() => void confirmAddToCollection()}
            >
              Add
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        title="Delete this paper?"
        entityName={toDelete ? toDelete.title || toDelete.name : null}
        description="It will be removed from your library and can no longer be opened in research workspaces."
        consequence="Evidence links and paper chats for this file may become unavailable."
        confirmLabel="Delete paper"
        destructive
        onConfirm={async () => {
          if (!toDelete) return;
          await deleteFile.mutateAsync(toDelete.id);
          toast.success("Paper deleted");
          setToDelete(null);
        }}
      />
    </PageContainer>
  );
}
