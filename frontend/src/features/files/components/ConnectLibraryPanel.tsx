import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useState,
} from "react";
import { useSearchParams } from "react-router-dom";
import { Loader2, Unplug } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/common/Toast";
import {
  libraryBridgeApi,
  type MendeleyFolder,
  type ZoteroCollection,
} from "../libraryBridgeApi";
import { LibraryImportDialog } from "./LibraryImportDialog";
import { cn } from "@/lib/utils";

export type ConnectLibraryPanelHandle = {
  openBibtex: () => void;
  openZoteroImport: () => void;
  openMendeleyImport: () => void;
};

/**
 * Quiet Sources strip for connected managers (PR1).
 * Connect lives in Sidebar → Integrations; this only surfaces import/sync when connected
 * or when deep-linked to connect.
 */
export const ConnectLibraryPanel = forwardRef<
  ConnectLibraryPanelHandle,
  {
    projectId?: number | null;
    onImported?: (projectId?: number | null) => void;
  }
>(function ConnectLibraryPanel({ projectId, onImported }, ref) {
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [importOpen, setImportOpen] = useState(false);
  const [zoteroOpen, setZoteroOpen] = useState(false);
  const [mendeleyOpen, setMendeleyOpen] = useState(false);
  const [collections, setCollections] = useState<ZoteroCollection[]>([]);
  const [folders, setFolders] = useState<MendeleyFolder[]>([]);
  const [collectionKey, setCollectionKey] = useState("all");
  const [folderId, setFolderId] = useState("all");
  const [createProject, setCreateProject] = useState(true);
  const [projectName, setProjectName] = useState("");
  const [busyKey, setBusyKey] = useState<
    null | "zotero" | "mendeley" | "zotero-import" | "mendeley-import" | "zotero-sync" | "mendeley-sync"
  >(null);

  const { data: connections } = useQuery({
    queryKey: ["library-connections"],
    queryFn: libraryBridgeApi.connections,
  });

  useEffect(() => {
    const z = searchParams.get("zotero");
    const m = searchParams.get("mendeley");
    if (!z && !m) return;
    if (z === "connected") toast.success("Zotero connected");
    else if (z === "denied") toast.error("Zotero authorization was denied");
    else if (z === "error") toast.error("Could not finish Zotero connection");
    else if (z === "not_configured") toast.error("Zotero is not configured on this server");
    if (m === "connected") toast.success("Mendeley connected");
    else if (m === "denied") toast.error("Mendeley authorization was denied");
    else if (m === "error") toast.error("Could not finish Mendeley connection");
    else if (m === "not_configured") toast.error("Mendeley is not configured on this server");
    const next = new URLSearchParams(searchParams);
    next.delete("zotero");
    next.delete("mendeley");
    setSearchParams(next, { replace: true });
    void qc.invalidateQueries({ queryKey: ["library-connections"] });
  }, [searchParams, setSearchParams, qc]);

  const connectZotero = async () => {
    setBusyKey("zotero");
    try {
      const res = await libraryBridgeApi.zoteroConnect();
      window.location.href = res.authorize_url;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Zotero connect failed");
      setBusyKey(null);
    }
  };

  const connectMendeley = async () => {
    setBusyKey("mendeley");
    try {
      const res = await libraryBridgeApi.mendeleyConnect();
      window.location.href = res.authorize_url;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Mendeley connect failed");
      setBusyKey(null);
    }
  };

  const openZoteroImport = async () => {
    setBusyKey("zotero-import");
    try {
      const res = await libraryBridgeApi.zoteroCollections();
      setCollections(res.items);
      setCollectionKey(res.items[0]?.key ?? "all");
      setCreateProject(true);
      setProjectName("");
      setZoteroOpen(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not load collections");
    } finally {
      setBusyKey(null);
    }
  };

  const openMendeleyImport = async () => {
    setBusyKey("mendeley-import");
    try {
      const res = await libraryBridgeApi.mendeleyFolders();
      setFolders(res.items);
      setFolderId(res.items[0]?.key ?? "all");
      setCreateProject(true);
      setProjectName("");
      setMendeleyOpen(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not load folders");
    } finally {
      setBusyKey(null);
    }
  };

  useImperativeHandle(ref, () => ({
    openBibtex: () => setImportOpen(true),
    openZoteroImport: () => void openZoteroImport(),
    openMendeleyImport: () => void openMendeleyImport(),
  }));

  /** Deep-links: ?provider=zotero|mendeley|bibtex */
  useEffect(() => {
    const provider = searchParams.get("provider");
    if (!provider) return;
    const t = window.setTimeout(() => {
      document.getElementById("import")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
      if (provider === "bibtex") setImportOpen(true);
      else if (provider === "zotero" && connections?.zotero?.connected) {
        void openZoteroImport();
      } else if (provider === "mendeley" && connections?.mendeley?.connected) {
        void openMendeleyImport();
      }
    }, 150);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- open once per provider deep-link
  }, [searchParams.get("provider"), connections?.zotero?.connected, connections?.mendeley?.connected]);

  const runZoteroImport = async () => {
    setBusyKey("zotero-import");
    try {
      const res = await libraryBridgeApi.zoteroImport({
        collection_key: collectionKey,
        create_project: createProject,
        project_name: projectName || undefined,
        project_id: createProject ? null : projectId,
      });
      toast.success(
        `Imported ${res.created} from Zotero` +
          (res.skipped ? ` · ${res.skipped} already in library` : ""),
      );
      setZoteroOpen(false);
      onImported?.(res.project_id);
      void qc.invalidateQueries({ queryKey: ["files"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Zotero import failed");
    } finally {
      setBusyKey(null);
    }
  };

  const runMendeleyImport = async () => {
    setBusyKey("mendeley-import");
    try {
      const res = await libraryBridgeApi.mendeleyImport({
        folder_id: folderId,
        create_project: createProject,
        project_name: projectName || undefined,
        project_id: createProject ? null : projectId,
      });
      toast.success(
        `Imported ${res.created} from Mendeley` +
          (res.skipped ? ` · ${res.skipped} already in library` : ""),
      );
      setMendeleyOpen(false);
      onImported?.(res.project_id);
      void qc.invalidateQueries({ queryKey: ["files"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Mendeley import failed");
    } finally {
      setBusyKey(null);
    }
  };

  const disconnectZotero = async () => {
    await libraryBridgeApi.zoteroDisconnect();
    toast.success("Zotero disconnected");
    void qc.invalidateQueries({ queryKey: ["library-connections"] });
  };

  const disconnectMendeley = async () => {
    await libraryBridgeApi.mendeleyDisconnect();
    toast.success("Mendeley disconnected");
    void qc.invalidateQueries({ queryKey: ["library-connections"] });
  };

  const syncZotero = async () => {
    setBusyKey("zotero-sync");
    try {
      const res = await libraryBridgeApi.zoteroSync();
      toast.success(
        `Zotero sync: ${res.created} new · ${res.updated} updated` +
          (res.conflicts ? ` · ${res.conflicts} conflicts` : ""),
      );
      void qc.invalidateQueries({ queryKey: ["files"] });
      void qc.invalidateQueries({ queryKey: ["library-connections"] });
      void qc.invalidateQueries({ queryKey: ["library-sync-runs"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Zotero sync failed");
    } finally {
      setBusyKey(null);
    }
  };

  const syncMendeley = async () => {
    setBusyKey("mendeley-sync");
    try {
      const res = await libraryBridgeApi.mendeleySync();
      toast.success(
        `Mendeley sync: ${res.created} new · ${res.updated} updated` +
          (res.conflicts ? ` · ${res.conflicts} conflicts` : ""),
      );
      void qc.invalidateQueries({ queryKey: ["files"] });
      void qc.invalidateQueries({ queryKey: ["library-connections"] });
      void qc.invalidateQueries({ queryKey: ["library-sync-runs"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Mendeley sync failed");
    } finally {
      setBusyKey(null);
    }
  };

  const zotero = connections?.zotero;
  const mendeley = connections?.mendeley;
  const focusProvider = searchParams.get("provider");
  const zoteroOn = Boolean(zotero?.connected);
  const mendeleyOn = Boolean(mendeley?.connected);
  const anyConnected = zoteroOn || mendeleyOn;
  const highlightZotero = focusProvider === "zotero";
  const highlightMendeley = focusProvider === "mendeley";
  const showConnectPrompt =
    !anyConnected && (highlightZotero || highlightMendeley);
  const showStrip = anyConnected || showConnectPrompt;

  return (
    <>
      {showStrip ? (
        <section
          id="import"
          className="scroll-mt-20 flex flex-wrap items-center gap-2 border-b border-border/60 pb-2 text-[12px]"
        >
          <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            Sources
          </span>
          {showConnectPrompt ? (
            <p className="text-[12px] text-muted-foreground">
              <button
                type="button"
                className="font-medium text-primary underline-offset-2 hover:underline"
                disabled={
                  highlightZotero
                    ? busyKey === "zotero" || zotero?.available === false
                    : busyKey === "mendeley" || mendeley?.available === false
                }
                onClick={() => void (highlightZotero ? connectZotero() : connectMendeley())}
              >
                {highlightZotero ? "Connect Zotero" : "Connect Mendeley"}
              </button>
              <span className="text-muted-foreground">
                {" "}
                — or use Integrations in the sidebar
              </span>
            </p>
          ) : (
            <>
              {zoteroOn && (
                <div
                  id="import-zotero"
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md",
                    highlightZotero && "ring-1 ring-primary/30",
                  )}
                >
                  <span className="text-muted-foreground">Zotero connected</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-[11px]"
                    disabled={busyKey === "zotero-import"}
                    onClick={openZoteroImport}
                  >
                    Import
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-[11px]"
                    disabled={busyKey === "zotero-sync"}
                    onClick={syncZotero}
                  >
                    {busyKey === "zotero-sync" ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      "Sync"
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1 text-muted-foreground"
                    onClick={disconnectZotero}
                    title="Disconnect"
                  >
                    <Unplug className="size-3" />
                  </Button>
                </div>
              )}
              {mendeleyOn && (
                <div
                  id="import-mendeley"
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md",
                    highlightMendeley && "ring-1 ring-primary/30",
                  )}
                >
                  <span className="text-muted-foreground">Mendeley connected</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-[11px]"
                    disabled={busyKey === "mendeley-import"}
                    onClick={openMendeleyImport}
                  >
                    Import
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-[11px]"
                    disabled={busyKey === "mendeley-sync"}
                    onClick={syncMendeley}
                  >
                    {busyKey === "mendeley-sync" ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      "Sync"
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1 text-muted-foreground"
                    onClick={disconnectMendeley}
                    title="Disconnect"
                  >
                    <Unplug className="size-3" />
                  </Button>
                </div>
              )}
            </>
          )}
          {!zoteroOn && <div id="import-zotero" className="sr-only" aria-hidden />}
          {!mendeleyOn && <div id="import-mendeley" className="sr-only" aria-hidden />}
        </section>
      ) : (
        <div id="import" className="sr-only" aria-hidden />
      )}

      <LibraryImportDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        projectId={projectId}
        onImported={onImported}
      />

      <Dialog open={zoteroOpen} onOpenChange={setZoteroOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Import from Zotero</DialogTitle>
            <DialogDescription>
              Choose a collection. Papers are deduped by DOI (then title + year).
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <div className="grid gap-1.5">
              <Label>Collection</Label>
              <select
                className="h-9 rounded-lg border border-border bg-transparent px-2 text-sm"
                value={collectionKey}
                onChange={(e) => setCollectionKey(e.target.value)}
              >
                {collections.map((c) => (
                  <option key={c.key} value={c.key}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={createProject}
                onChange={(e) => setCreateProject(e.target.checked)}
              />
              Create a new project from this import (optional)
            </label>
            {createProject && (
              <Input
                value={projectName}
                placeholder="Project name"
                onChange={(e) => setProjectName(e.target.value)}
              />
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setZoteroOpen(false)}>
              Cancel
            </Button>
            <Button disabled={busyKey === "zotero-import"} onClick={runZoteroImport}>
              {busyKey === "zotero-import" ? <Loader2 className="size-4 animate-spin" /> : null}
              Import
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={mendeleyOpen} onOpenChange={setMendeleyOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Import from Mendeley</DialogTitle>
            <DialogDescription>
              Choose a folder. Metadata-only stubs are created (same pipeline as Zotero).
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <div className="grid gap-1.5">
              <Label>Folder</Label>
              <select
                className="h-9 rounded-lg border border-border bg-transparent px-2 text-sm"
                value={folderId}
                onChange={(e) => setFolderId(e.target.value)}
              >
                {folders.map((f) => (
                  <option key={f.key} value={f.key}>
                    {f.name}
                  </option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={createProject}
                onChange={(e) => setCreateProject(e.target.checked)}
              />
              Create a new project from this import (optional)
            </label>
            {createProject && (
              <Input
                value={projectName}
                placeholder="Project name"
                onChange={(e) => setProjectName(e.target.value)}
              />
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMendeleyOpen(false)}>
              Cancel
            </Button>
            <Button disabled={busyKey === "mendeley-import"} onClick={runMendeleyImport}>
              {busyKey === "mendeley-import" ? <Loader2 className="size-4 animate-spin" /> : null}
              Import
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
});
