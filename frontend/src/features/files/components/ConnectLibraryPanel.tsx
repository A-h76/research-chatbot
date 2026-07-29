import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Check, Download, Link2, Loader2, Unplug } from "lucide-react";
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

export function ConnectLibraryPanel({
  projectId,
  onImported,
}: {
  projectId?: number | null;
  onImported?: (projectId?: number | null) => void;
}) {
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
  const [busy, setBusy] = useState(false);

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

  /** Sidebar deep-links: ?provider=zotero|mendeley|upload + #import */
  useEffect(() => {
    const provider = searchParams.get("provider");
    if (!provider) return;
    const t = window.setTimeout(() => {
      document.getElementById("import")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
      if (provider === "zotero") {
        document.getElementById("import-zotero")?.focus();
      } else if (provider === "mendeley") {
        document.getElementById("import-mendeley")?.focus();
      } else if (provider === "upload") {
        document.getElementById("library-upload-input")?.click();
      }
    }, 120);
    return () => window.clearTimeout(t);
  }, [searchParams]);

  const connectZotero = async () => {
    setBusy(true);
    try {
      const res = await libraryBridgeApi.zoteroConnect();
      window.location.href = res.authorize_url;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Zotero connect failed");
      setBusy(false);
    }
  };

  const connectMendeley = async () => {
    setBusy(true);
    try {
      const res = await libraryBridgeApi.mendeleyConnect();
      window.location.href = res.authorize_url;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Mendeley connect failed");
      setBusy(false);
    }
  };

  const openZoteroImport = async () => {
    setBusy(true);
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
      setBusy(false);
    }
  };

  const openMendeleyImport = async () => {
    setBusy(true);
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
      setBusy(false);
    }
  };

  const runZoteroImport = async () => {
    setBusy(true);
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
      setBusy(false);
    }
  };

  const runMendeleyImport = async () => {
    setBusy(true);
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
      setBusy(false);
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
    setBusy(true);
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
      setBusy(false);
    }
  };

  const syncMendeley = async () => {
    setBusy(true);
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
      setBusy(false);
    }
  };

  const { data: syncRuns } = useQuery({
    queryKey: ["library-sync-runs"],
    queryFn: () => libraryBridgeApi.syncRuns(),
    enabled: Boolean(connections?.zotero?.connected || connections?.mendeley?.connected),
  });

  const zotero = connections?.zotero;
  const mendeley = connections?.mendeley;
  const focusProvider = searchParams.get("provider");

  return (
    <>
      <section id="import" className="scroll-mt-20 rounded-xl border border-border bg-card/40 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Import research</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Upload PDFs or connect Zotero / Mendeley — trust signals for your workflow.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => setImportOpen(true)}>
              BibTeX / RIS
            </Button>
            <a
              href={libraryBridgeApi.exportUrl("bibtex", projectId)}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border px-2.5 text-xs font-medium hover:bg-muted"
            >
              <Download className="size-3.5" /> BibTeX
            </a>
            <a
              href={libraryBridgeApi.exportUrl("ris", projectId)}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border px-2.5 text-xs font-medium hover:bg-muted"
            >
              <Download className="size-3.5" /> RIS
            </a>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div
            id="import-zotero"
            tabIndex={-1}
            className={cn(
              "rounded-lg border p-3 outline-none transition-colors",
              focusProvider === "zotero"
                ? "border-primary/50 bg-primary/5 ring-2 ring-primary/20"
                : "border-border",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm font-medium">Zotero</p>
                <p className="text-xs text-muted-foreground">
                  {zotero?.connected
                    ? `Connected${zotero.username ? ` as ${zotero.username}` : ""}`
                    : "Import a collection into Dhund"}
                </p>
              </div>
              {zotero?.connected ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-400">
                  <Check className="size-3" /> Connected
                </span>
              ) : null}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {!zotero?.connected ? (
                <Button
                  size="sm"
                  disabled={busy || zotero?.available === false}
                  onClick={connectZotero}
                  title={
                    zotero?.available === false
                      ? `Missing on server: ${(zotero.missing_env ?? ["ZOTERO_CLIENT_KEY", "ZOTERO_CLIENT_SECRET"]).join(", ")}`
                      : undefined
                  }
                >
                  {busy ? <Loader2 className="size-3.5 animate-spin" /> : <Link2 className="size-3.5" />}
                  {zotero?.available === false ? "Server OAuth not set" : "Connect Zotero"}
                </Button>
              ) : (
                <>
                  <Button size="sm" disabled={busy} onClick={openZoteroImport}>
                    Import collection
                  </Button>
                  <Button size="sm" variant="outline" disabled={busy} onClick={syncZotero}>
                    Sync now
                  </Button>
                  <Button size="sm" variant="ghost" onClick={disconnectZotero}>
                    <Unplug className="size-3.5" /> Disconnect
                  </Button>
                </>
              )}
            </div>
            {zotero?.connected && zotero.last_synced_at && (
              <p className="mt-2 text-[11px] text-muted-foreground">
                Last sync {new Date(zotero.last_synced_at).toLocaleString()}
              </p>
            )}
            {zotero?.available === false && (
              <p className="mt-2 text-[11px] text-muted-foreground">
                Set{" "}
                <code className="text-[10px]">
                  {(zotero.missing_env ?? ["ZOTERO_CLIENT_KEY", "ZOTERO_CLIENT_SECRET"]).join(
                    " + ",
                  )}
                </code>{" "}
                on the <strong>deployed</strong> host (Railway Variables). Local{" "}
                <code className="text-[10px]">.env</code> is not shipped in Docker. Or import
                BibTeX/RIS above.
              </p>
            )}
          </div>

          <div
            id="import-mendeley"
            tabIndex={-1}
            className={cn(
              "rounded-lg border p-3 outline-none transition-colors",
              focusProvider === "mendeley"
                ? "border-primary/50 bg-primary/5 ring-2 ring-primary/20"
                : "border-border",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm font-medium">Mendeley</p>
                <p className="text-xs text-muted-foreground">
                  {mendeley?.connected
                    ? `Connected${mendeley.username ? ` as ${mendeley.username}` : ""}`
                    : "Import a folder into Dhund"}
                </p>
              </div>
              {mendeley?.connected ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-400">
                  <Check className="size-3" /> Connected
                </span>
              ) : null}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {!mendeley?.connected ? (
                <Button
                  size="sm"
                  disabled={busy || mendeley?.available === false}
                  onClick={connectMendeley}
                  title={
                    mendeley?.available === false
                      ? `Missing on server: ${(mendeley.missing_env ?? ["MENDELEY_CLIENT_ID", "MENDELEY_CLIENT_SECRET"]).join(", ")}`
                      : undefined
                  }
                >
                  {busy ? <Loader2 className="size-3.5 animate-spin" /> : <Link2 className="size-3.5" />}
                  {mendeley?.available === false ? "Server OAuth not set" : "Connect Mendeley"}
                </Button>
              ) : (
                <>
                  <Button size="sm" disabled={busy} onClick={openMendeleyImport}>
                    Import folder
                  </Button>
                  <Button size="sm" variant="outline" disabled={busy} onClick={syncMendeley}>
                    Sync now
                  </Button>
                  <Button size="sm" variant="ghost" onClick={disconnectMendeley}>
                    <Unplug className="size-3.5" /> Disconnect
                  </Button>
                </>
              )}
            </div>
            {mendeley?.connected && mendeley.last_synced_at && (
              <p className="mt-2 text-[11px] text-muted-foreground">
                Last sync {new Date(mendeley.last_synced_at).toLocaleString()}
              </p>
            )}
            {mendeley?.available === false && (
              <p className="mt-2 text-[11px] text-muted-foreground">
                Set{" "}
                <code className="text-[10px]">
                  {(mendeley.missing_env ?? ["MENDELEY_CLIENT_ID", "MENDELEY_CLIENT_SECRET"]).join(
                    " + ",
                  )}
                </code>{" "}
                on the <strong>deployed</strong> host (Railway Variables). Local{" "}
                <code className="text-[10px]">.env</code> is not shipped in Docker. Or import
                BibTeX/RIS above.
              </p>
            )}
          </div>
        </div>

        {syncRuns?.items && syncRuns.items.length > 0 && (
          <div className="mt-4 border-t border-border pt-3">
            <p className="text-xs font-medium text-muted-foreground">Recent syncs</p>
            <ul className="mt-1.5 space-y-1">
              {syncRuns.items.slice(0, 5).map((r) => (
                <li key={r.id} className="flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                  <span className="capitalize">{r.provider}</span>
                  <span>· {r.status}</span>
                  <span>
                    · +{r.created} / ~{r.updated}
                    {r.conflicts ? ` / !${r.conflicts}` : ""}
                  </span>
                  {r.started_at && (
                    <span>· {new Date(r.started_at).toLocaleString()}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

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
              Collections stay as Library folders unless you create a project.
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
            <Button disabled={busy} onClick={runZoteroImport}>
              {busy ? <Loader2 className="size-4 animate-spin" /> : null}
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
              Create a project only when the folder is a real research effort.
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
            <Button disabled={busy} onClick={runMendeleyImport}>
              {busy ? <Loader2 className="size-4 animate-spin" /> : null}
              Import
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
