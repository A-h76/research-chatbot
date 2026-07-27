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
import { libraryBridgeApi, type ZoteroCollection } from "../libraryBridgeApi";
import { LibraryImportDialog } from "./LibraryImportDialog";

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
  const [collections, setCollections] = useState<ZoteroCollection[]>([]);
  const [collectionKey, setCollectionKey] = useState("all");
  const [createProject, setCreateProject] = useState(true);
  const [projectName, setProjectName] = useState("");
  const [busy, setBusy] = useState(false);

  const { data: connections } = useQuery({
    queryKey: ["library-connections"],
    queryFn: libraryBridgeApi.connections,
  });

  useEffect(() => {
    const z = searchParams.get("zotero");
    if (!z) return;
    if (z === "connected") toast.success("Zotero connected");
    else if (z === "denied") toast.error("Zotero authorization was denied");
    else if (z === "error") toast.error("Could not finish Zotero connection");
    else if (z === "not_configured") toast.error("Zotero is not configured on this server");
    const next = new URLSearchParams(searchParams);
    next.delete("zotero");
    setSearchParams(next, { replace: true });
    void qc.invalidateQueries({ queryKey: ["library-connections"] });
  }, [searchParams, setSearchParams, qc]);

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

  const openZoteroImport = async () => {
    setBusy(true);
    try {
      const res = await libraryBridgeApi.zoteroCollections();
      setCollections(res.items);
      setCollectionKey(res.items[0]?.key ?? "all");
      setZoteroOpen(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not load collections");
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

  const disconnectZotero = async () => {
    await libraryBridgeApi.zoteroDisconnect();
    toast.success("Zotero disconnected");
    void qc.invalidateQueries({ queryKey: ["library-connections"] });
  };

  const zotero = connections?.zotero;
  const mendeley = connections?.mendeley;

  return (
    <>
      <section className="rounded-xl border border-border bg-card/40 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Import library</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Bring your existing research into Dhund — no re-upload one-by-one.
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
          <div className="rounded-lg border border-border p-3">
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
                      ? "Set ZOTERO_CLIENT_KEY / SECRET on the server"
                      : undefined
                  }
                >
                  {busy ? <Loader2 className="size-3.5 animate-spin" /> : <Link2 className="size-3.5" />}
                  {zotero?.available === false ? "Not configured" : "Connect Zotero"}
                </Button>
              ) : (
                <>
                  <Button size="sm" disabled={busy} onClick={openZoteroImport}>
                    Import collection
                  </Button>
                  <Button size="sm" variant="ghost" onClick={disconnectZotero}>
                    <Unplug className="size-3.5" /> Disconnect
                  </Button>
                </>
              )}
            </div>
            {zotero?.available === false && (
              <p className="mt-2 text-[11px] text-muted-foreground">
                Or export BibTeX/RIS from Zotero and import above — works today.
              </p>
            )}
          </div>

          <div className="rounded-lg border border-border p-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm font-medium">Mendeley</p>
                <p className="text-xs text-muted-foreground">
                  {mendeley?.coming_soon
                    ? "One-click import coming soon"
                    : "Import your Mendeley library"}
                </p>
              </div>
              <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
                Coming soon
              </span>
            </div>
            <div className="mt-3">
              <Button size="sm" variant="outline" onClick={() => setImportOpen(true)}>
                Import via BibTeX / RIS
              </Button>
            </div>
          </div>
        </div>
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
              Create a new project from this import
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
    </>
  );
}
