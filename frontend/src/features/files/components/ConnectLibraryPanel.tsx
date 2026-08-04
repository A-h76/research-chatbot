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
  type DrivePdfFile,
  type LibrarySyncRun,
  type MendeleyFolder,
  type ZoteroCollection,
} from "../libraryBridgeApi";
import { LibraryImportDialog } from "./LibraryImportDialog";
import { cn } from "@/lib/utils";

async function pollSyncRun(runId: number, timeoutMs = 120_000): Promise<LibrarySyncRun> {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const run = await libraryBridgeApi.syncRun(runId);
    if (run.status === "ok") return run;
    if (run.status === "error") {
      throw new Error(run.error || "Sync failed");
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  throw new Error("Sync timed out — check sync history or try again");
}

export type ConnectLibraryPanelHandle = {
  openBibtex: () => void;
  openZoteroImport: () => void;
  openMendeleyImport: () => void;
  openGoogleDriveImport: () => void;
  openDropboxImport: () => void;
  openOneDriveImport: () => void;
};

/**
 * Quiet Sources strip for connected managers (PR1).
 * Connect lives in Settings → Integrations; this only surfaces import/sync when connected
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
  const [driveOpen, setDriveOpen] = useState(false);
  const [dropboxOpen, setDropboxOpen] = useState(false);
  const [onedriveOpen, setOnedriveOpen] = useState(false);
  const [collections, setCollections] = useState<ZoteroCollection[]>([]);
  const [folders, setFolders] = useState<MendeleyFolder[]>([]);
  const [driveFiles, setDriveFiles] = useState<DrivePdfFile[]>([]);
  const [dropboxFiles, setDropboxFiles] = useState<DrivePdfFile[]>([]);
  const [onedriveFiles, setOnedriveFiles] = useState<DrivePdfFile[]>([]);
  const [driveFolderId, setDriveFolderId] = useState("root");
  const [dropboxFolderId, setDropboxFolderId] = useState("");
  const [onedriveFolderId, setOnedriveFolderId] = useState("root");
  const [selectedDriveIds, setSelectedDriveIds] = useState<string[]>([]);
  const [selectedDropboxIds, setSelectedDropboxIds] = useState<string[]>([]);
  const [selectedOnedriveIds, setSelectedOnedriveIds] = useState<string[]>([]);
  const [collectionKey, setCollectionKey] = useState("all");
  const [folderId, setFolderId] = useState("all");
  const [createProject, setCreateProject] = useState(true);
  const [projectName, setProjectName] = useState("");
  const [busyKey, setBusyKey] = useState<
    | null
    | "zotero"
    | "mendeley"
    | "google_drive"
    | "dropbox"
    | "onedrive"
    | "zotero-import"
    | "mendeley-import"
    | "drive-import"
    | "dropbox-import"
    | "onedrive-import"
    | "zotero-sync"
    | "mendeley-sync"
    | "zotero-pull"
    | "mendeley-pull"
  >(null);

  const { data: connections } = useQuery({
    queryKey: ["library-connections"],
    queryFn: libraryBridgeApi.connections,
  });

  useEffect(() => {
    const z = searchParams.get("zotero");
    const m = searchParams.get("mendeley");
    const g = searchParams.get("google_drive");
    const dbx = searchParams.get("dropbox");
    const od = searchParams.get("onedrive");
    if (!z && !m && !g && !dbx && !od) return;
    if (z === "connected") toast.success("Zotero connected");
    else if (z === "denied") toast.error("Zotero authorization was denied");
    else if (z === "error") toast.error("Could not finish Zotero connection");
    else if (z === "not_configured") toast.error("Zotero is not configured on this server");
    if (m === "connected") toast.success("Mendeley connected");
    else if (m === "denied") toast.error("Mendeley authorization was denied");
    else if (m === "error") toast.error("Could not finish Mendeley connection");
    else if (m === "not_configured") toast.error("Mendeley is not configured on this server");
    if (g === "connected") toast.success("Google Drive connected");
    else if (g === "denied") toast.error("Google Drive authorization was denied");
    else if (g === "error") toast.error("Could not finish Google Drive connection");
    else if (g === "not_configured") toast.error("Google Drive is not configured on this server");
    if (dbx === "connected") toast.success("Dropbox connected");
    else if (dbx === "denied") toast.error("Dropbox authorization was denied");
    else if (dbx === "error") toast.error("Could not finish Dropbox connection");
    else if (dbx === "not_configured") toast.error("Dropbox is not configured on this server");
    if (od === "connected") toast.success("OneDrive connected");
    else if (od === "denied") toast.error("OneDrive authorization was denied");
    else if (od === "error") toast.error("Could not finish OneDrive connection");
    else if (od === "not_configured") toast.error("OneDrive is not configured on this server");
    const next = new URLSearchParams(searchParams);
    next.delete("zotero");
    next.delete("mendeley");
    next.delete("google_drive");
    next.delete("dropbox");
    next.delete("onedrive");
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

  const openGoogleDriveImport = async () => {
    setBusyKey("drive-import");
    try {
      const res = await libraryBridgeApi.googleDriveFiles({ folder_id: "root", limit: 50 });
      setDriveFiles(res.items);
      setDriveFolderId(res.folder_id || "root");
      setSelectedDriveIds([]);
      setDriveOpen(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not load Drive files");
    } finally {
      setBusyKey(null);
    }
  };

  const openDropboxImport = async () => {
    setBusyKey("dropbox-import");
    try {
      const res = await libraryBridgeApi.dropboxFiles({ folder_id: "", limit: 50 });
      setDropboxFiles(res.items);
      setDropboxFolderId(res.folder_id === "root" ? "" : res.folder_id || "");
      setSelectedDropboxIds([]);
      setDropboxOpen(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not load Dropbox files");
    } finally {
      setBusyKey(null);
    }
  };

  const openOneDriveImport = async () => {
    setBusyKey("onedrive-import");
    try {
      const res = await libraryBridgeApi.onedriveFiles({ folder_id: "root", limit: 50 });
      setOnedriveFiles(res.items);
      setOnedriveFolderId(res.folder_id || "root");
      setSelectedOnedriveIds([]);
      setOnedriveOpen(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not load OneDrive files");
    } finally {
      setBusyKey(null);
    }
  };

  useImperativeHandle(ref, () => ({
    openBibtex: () => setImportOpen(true),
    openZoteroImport: () => void openZoteroImport(),
    openMendeleyImport: () => void openMendeleyImport(),
    openGoogleDriveImport: () => void openGoogleDriveImport(),
    openDropboxImport: () => void openDropboxImport(),
    openOneDriveImport: () => void openOneDriveImport(),
  }));

  /** Deep-links: ?provider=zotero|mendeley|bibtex|google_drive|dropbox|onedrive */
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
      } else if (provider === "google_drive" && connections?.google_drive?.connected) {
        void openGoogleDriveImport();
      } else if (provider === "dropbox" && connections?.dropbox?.connected) {
        void openDropboxImport();
      } else if (provider === "onedrive" && connections?.onedrive?.connected) {
        void openOneDriveImport();
      }
    }, 150);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- open once per provider deep-link
  }, [
    searchParams.get("provider"),
    connections?.zotero?.connected,
    connections?.mendeley?.connected,
    connections?.google_drive?.connected,
    connections?.dropbox?.connected,
    connections?.onedrive?.connected,
  ]);

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
      if (res.status === "queued" && res.sync_run_id != null) {
        toast.success("Zotero sync queued…");
        const final = await pollSyncRun(res.sync_run_id);
        toast.success(
          `Zotero sync: ${final.created} new · ${final.updated} updated` +
            (final.conflicts ? ` · ${final.conflicts} conflicts` : ""),
        );
      } else {
        toast.success(
          `Zotero sync: ${res.created ?? 0} new · ${res.updated ?? 0} updated` +
            (res.conflicts ? ` · ${res.conflicts} conflicts` : ""),
        );
      }
      void qc.invalidateQueries({ queryKey: ["files"] });
      void qc.invalidateQueries({ queryKey: ["library-connections"] });
      void qc.invalidateQueries({ queryKey: ["library-sync-runs"] });
      void qc.invalidateQueries({ queryKey: ["library"] });
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
      if (res.status === "queued" && res.sync_run_id != null) {
        toast.success("Mendeley sync queued…");
        const final = await pollSyncRun(res.sync_run_id);
        toast.success(
          `Mendeley sync: ${final.created} new · ${final.updated} updated` +
            (final.conflicts ? ` · ${final.conflicts} conflicts` : ""),
        );
      } else {
        toast.success(
          `Mendeley sync: ${res.created ?? 0} new · ${res.updated ?? 0} updated` +
            (res.conflicts ? ` · ${res.conflicts} conflicts` : ""),
        );
      }
      void qc.invalidateQueries({ queryKey: ["files"] });
      void qc.invalidateQueries({ queryKey: ["library-connections"] });
      void qc.invalidateQueries({ queryKey: ["library-sync-runs"] });
      void qc.invalidateQueries({ queryKey: ["library"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Mendeley sync failed");
    } finally {
      setBusyKey(null);
    }
  };

  const pullZoteroPdfs = async () => {
    setBusyKey("zotero-pull");
    try {
      const res = await libraryBridgeApi.pullZoteroPdfs({ limit: 20 });
      toast.success(
        `Pulled ${res.pulled ?? 0} PDF${(res.pulled ?? 0) === 1 ? "" : "s"}` +
          (res.queued ? ` · ${res.queued} queued for analysis` : ""),
      );
      void qc.invalidateQueries({ queryKey: ["files"] });
      void qc.invalidateQueries({ queryKey: ["library"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "PDF pull failed");
    } finally {
      setBusyKey(null);
    }
  };

  const pullMendeleyPdfs = async () => {
    setBusyKey("mendeley-pull");
    try {
      const res = await libraryBridgeApi.pullMendeleyPdfs({ limit: 20 });
      toast.success(
        `Pulled ${res.pulled ?? 0} PDF${(res.pulled ?? 0) === 1 ? "" : "s"}` +
          (res.queued ? ` · ${res.queued} queued for analysis` : ""),
      );
      void qc.invalidateQueries({ queryKey: ["files"] });
      void qc.invalidateQueries({ queryKey: ["library"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "PDF pull failed");
    } finally {
      setBusyKey(null);
    }
  };

  const runDriveImport = async () => {
    if (selectedDriveIds.length === 0) {
      toast.error("Select at least one PDF");
      return;
    }
    setBusyKey("drive-import");
    try {
      const res = await libraryBridgeApi.googleDriveImport({
        file_ids: selectedDriveIds,
        project_id: projectId ?? null,
        folder_id: driveFolderId,
      });
      toast.success(
        `Imported ${res.created} from Drive` +
          (res.queued ? ` · ${res.queued} queued for Analysis 2.0` : "") +
          (Array.isArray(res.skipped) && res.skipped.length
            ? ` · ${res.skipped.length} already in library`
            : ""),
      );
      setDriveOpen(false);
      onImported?.(res.project_id);
      void qc.invalidateQueries({ queryKey: ["files"] });
      void qc.invalidateQueries({ queryKey: ["library"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Drive import failed");
    } finally {
      setBusyKey(null);
    }
  };

  const disconnectDrive = async () => {
    await libraryBridgeApi.googleDriveDisconnect();
    toast.success("Google Drive disconnected");
    void qc.invalidateQueries({ queryKey: ["library-connections"] });
  };

  const runDropboxImport = async () => {
    if (selectedDropboxIds.length === 0) {
      toast.error("Select at least one PDF");
      return;
    }
    setBusyKey("dropbox-import");
    try {
      const res = await libraryBridgeApi.dropboxImport({
        file_ids: selectedDropboxIds,
        project_id: projectId ?? null,
        folder_id: dropboxFolderId,
      });
      toast.success(
        `Imported ${res.created} from Dropbox` +
          (res.queued ? ` · ${res.queued} queued for Analysis 2.0` : "") +
          (Array.isArray(res.skipped) && res.skipped.length
            ? ` · ${res.skipped.length} already in library`
            : ""),
      );
      setDropboxOpen(false);
      onImported?.(res.project_id);
      void qc.invalidateQueries({ queryKey: ["files"] });
      void qc.invalidateQueries({ queryKey: ["library"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Dropbox import failed");
    } finally {
      setBusyKey(null);
    }
  };

  const disconnectDropbox = async () => {
    await libraryBridgeApi.dropboxDisconnect();
    toast.success("Dropbox disconnected");
    void qc.invalidateQueries({ queryKey: ["library-connections"] });
  };

  const runOneDriveImport = async () => {
    if (selectedOnedriveIds.length === 0) {
      toast.error("Select at least one PDF");
      return;
    }
    setBusyKey("onedrive-import");
    try {
      const res = await libraryBridgeApi.onedriveImport({
        file_ids: selectedOnedriveIds,
        project_id: projectId ?? null,
        folder_id: onedriveFolderId,
      });
      toast.success(
        `Imported ${res.created} from OneDrive` +
          (res.queued ? ` · ${res.queued} queued for Analysis 2.0` : "") +
          (Array.isArray(res.skipped) && res.skipped.length
            ? ` · ${res.skipped.length} already in library`
            : ""),
      );
      setOnedriveOpen(false);
      onImported?.(res.project_id);
      void qc.invalidateQueries({ queryKey: ["files"] });
      void qc.invalidateQueries({ queryKey: ["library"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "OneDrive import failed");
    } finally {
      setBusyKey(null);
    }
  };

  const disconnectOneDrive = async () => {
    await libraryBridgeApi.onedriveDisconnect();
    toast.success("OneDrive disconnected");
    void qc.invalidateQueries({ queryKey: ["library-connections"] });
  };

  const toggleDriveFile = (id: string) => {
    setSelectedDriveIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const toggleDropboxFile = (id: string) => {
    setSelectedDropboxIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const toggleOnedriveFile = (id: string) => {
    setSelectedOnedriveIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const zotero = connections?.zotero;
  const mendeley = connections?.mendeley;
  const drive = connections?.google_drive;
  const dropbox = connections?.dropbox;
  const onedrive = connections?.onedrive;
  const focusProvider = searchParams.get("provider");
  const zoteroOn = Boolean(zotero?.connected);
  const mendeleyOn = Boolean(mendeley?.connected);
  const driveOn = Boolean(drive?.connected);
  const dropboxOn = Boolean(dropbox?.connected);
  const onedriveOn = Boolean(onedrive?.connected);
  const anyConnected = zoteroOn || mendeleyOn || driveOn || dropboxOn || onedriveOn;
  const highlightZotero = focusProvider === "zotero";
  const highlightMendeley = focusProvider === "mendeley";
  const highlightDrive = focusProvider === "google_drive";
  const highlightDropbox = focusProvider === "dropbox";
  const highlightOnedrive = focusProvider === "onedrive";
  const showConnectPrompt =
    !anyConnected &&
    (highlightZotero ||
      highlightMendeley ||
      highlightDrive ||
      highlightDropbox ||
      highlightOnedrive);
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
                onClick={() => {
                  window.location.href = "/settings/integrations";
                }}
              >
                {highlightDropbox
                  ? "Connect Dropbox"
                  : highlightOnedrive
                    ? "Connect OneDrive"
                    : highlightDrive
                      ? "Connect Google Drive"
                      : highlightZotero
                        ? "Connect Zotero"
                        : "Connect Mendeley"}
              </button>
              <span className="text-muted-foreground">
                {" "}
                — or open Settings → Integrations
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
                    className="h-6 px-1.5 text-[11px]"
                    disabled={busyKey === "zotero-pull"}
                    onClick={() => void pullZoteroPdfs()}
                    title="Pull PDFs from Zotero onto stubs missing a file"
                  >
                    {busyKey === "zotero-pull" ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      "Pull PDFs"
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
                    className="h-6 px-1.5 text-[11px]"
                    disabled={busyKey === "mendeley-pull"}
                    onClick={() => void pullMendeleyPdfs()}
                    title="Pull PDFs from Mendeley onto stubs missing a file"
                  >
                    {busyKey === "mendeley-pull" ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      "Pull PDFs"
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
              {driveOn && (
                <div
                  id="import-google-drive"
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md",
                    highlightDrive && "ring-1 ring-primary/30",
                  )}
                >
                  <span className="text-muted-foreground">Drive connected</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-[11px]"
                    disabled={busyKey === "drive-import"}
                    onClick={() => void openGoogleDriveImport()}
                  >
                    Import PDFs
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1 text-muted-foreground"
                    onClick={() => void disconnectDrive()}
                    title="Disconnect"
                  >
                    <Unplug className="size-3" />
                  </Button>
                </div>
              )}
              {dropboxOn && (
                <div
                  id="import-dropbox"
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md",
                    highlightDropbox && "ring-1 ring-primary/30",
                  )}
                >
                  <span className="text-muted-foreground">Dropbox connected</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-[11px]"
                    disabled={busyKey === "dropbox-import"}
                    onClick={() => void openDropboxImport()}
                  >
                    Import PDFs
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1 text-muted-foreground"
                    onClick={() => void disconnectDropbox()}
                    title="Disconnect"
                  >
                    <Unplug className="size-3" />
                  </Button>
                </div>
              )}
              {onedriveOn && (
                <div
                  id="import-onedrive"
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md",
                    highlightOnedrive && "ring-1 ring-primary/30",
                  )}
                >
                  <span className="text-muted-foreground">OneDrive connected</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1.5 text-[11px]"
                    disabled={busyKey === "onedrive-import"}
                    onClick={() => void openOneDriveImport()}
                  >
                    Import PDFs
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 px-1 text-muted-foreground"
                    onClick={() => void disconnectOneDrive()}
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
          {!driveOn && <div id="import-google-drive" className="sr-only" aria-hidden />}
          {!dropboxOn && <div id="import-dropbox" className="sr-only" aria-hidden />}
          {!onedriveOn && <div id="import-onedrive" className="sr-only" aria-hidden />}
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

      <Dialog open={driveOpen} onOpenChange={setDriveOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Import from Google Drive</DialogTitle>
            <DialogDescription>
              Select PDFs from My Drive. Each file enters the shared Analysis 2.0 pipeline.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-72 space-y-1 overflow-y-auto rounded-lg border border-border p-2">
            {driveFiles.length === 0 ? (
              <p className="p-3 text-sm text-muted-foreground">
                No PDFs found in this folder.
              </p>
            ) : (
              driveFiles.map((f) => {
                const checked = selectedDriveIds.includes(f.id);
                return (
                  <label
                    key={f.id}
                    className="flex cursor-pointer items-start gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted/60"
                  >
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={checked}
                      onChange={() => toggleDriveFile(f.id)}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium">{f.name}</span>
                      {f.size > 0 && (
                        <span className="text-[11px] text-muted-foreground">
                          {(f.size / 1024).toFixed(0)} KB
                        </span>
                      )}
                    </span>
                  </label>
                );
              })
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDriveOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={busyKey === "drive-import" || selectedDriveIds.length === 0}
              onClick={() => void runDriveImport()}
            >
              {busyKey === "drive-import" ? <Loader2 className="size-4 animate-spin" /> : null}
              Import {selectedDriveIds.length || ""} into Library
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dropboxOpen} onOpenChange={setDropboxOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Import from Dropbox</DialogTitle>
            <DialogDescription>
              Select PDFs from your Dropbox. Each file enters the shared Analysis 2.0 pipeline.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-72 space-y-1 overflow-y-auto rounded-lg border border-border p-2">
            {dropboxFiles.length === 0 ? (
              <p className="p-3 text-sm text-muted-foreground">
                No PDFs found in this folder.
              </p>
            ) : (
              dropboxFiles.map((f) => {
                const checked = selectedDropboxIds.includes(f.id);
                return (
                  <label
                    key={f.id}
                    className="flex cursor-pointer items-start gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted/60"
                  >
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={checked}
                      onChange={() => toggleDropboxFile(f.id)}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium">{f.name}</span>
                      {f.size > 0 && (
                        <span className="text-[11px] text-muted-foreground">
                          {(f.size / 1024).toFixed(0)} KB
                        </span>
                      )}
                    </span>
                  </label>
                );
              })
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDropboxOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={busyKey === "dropbox-import" || selectedDropboxIds.length === 0}
              onClick={() => void runDropboxImport()}
            >
              {busyKey === "dropbox-import" ? <Loader2 className="size-4 animate-spin" /> : null}
              Import {selectedDropboxIds.length || ""} into Library
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={onedriveOpen} onOpenChange={setOnedriveOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Import from OneDrive</DialogTitle>
            <DialogDescription>
              Select PDFs from your OneDrive. Each file enters the shared Analysis 2.0 pipeline.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-72 space-y-1 overflow-y-auto rounded-lg border border-border p-2">
            {onedriveFiles.length === 0 ? (
              <p className="p-3 text-sm text-muted-foreground">
                No PDFs found in this folder.
              </p>
            ) : (
              onedriveFiles.map((f) => {
                const checked = selectedOnedriveIds.includes(f.id);
                return (
                  <label
                    key={f.id}
                    className="flex cursor-pointer items-start gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted/60"
                  >
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={checked}
                      onChange={() => toggleOnedriveFile(f.id)}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium">{f.name}</span>
                      {f.size > 0 && (
                        <span className="text-[11px] text-muted-foreground">
                          {(f.size / 1024).toFixed(0)} KB
                        </span>
                      )}
                    </span>
                  </label>
                );
              })
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOnedriveOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={busyKey === "onedrive-import" || selectedOnedriveIds.length === 0}
              onClick={() => void runOneDriveImport()}
            >
              {busyKey === "onedrive-import" ? <Loader2 className="size-4 animate-spin" /> : null}
              Import {selectedOnedriveIds.length || ""} into Library
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
});
