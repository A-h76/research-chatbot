import { useState } from "react";
import { FileUp, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "@/components/common/Toast";
import { libraryBridgeApi, type LibraryFormat } from "../libraryBridgeApi";

export function LibraryImportDialog({
  open,
  onOpenChange,
  projectId,
  onImported,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  projectId?: number | null;
  onImported?: (projectId?: number | null) => void;
}) {
  const [format, setFormat] = useState<LibraryFormat>("bibtex");
  const [createProject, setCreateProject] = useState(true);
  const [projectName, setProjectName] = useState("");
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  const submit = async () => {
    if (!file) {
      toast.error("Choose a .bib or .ris file");
      return;
    }
    setBusy(true);
    try {
      const res = await libraryBridgeApi.importFile(file, {
        format,
        project_id: createProject ? null : projectId,
        create_project: createProject,
        project_name: projectName || undefined,
      });
      toast.success(
        `Imported ${res.created} paper${res.created === 1 ? "" : "s"}` +
          (res.skipped ? ` · ${res.skipped} already in library` : ""),
      );
      onOpenChange(false);
      setFile(null);
      onImported?.(res.project_id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Import library</DialogTitle>
          <DialogDescription>
            Bring papers from Zotero, Mendeley, or any tool that exports BibTeX or RIS.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3">
          <div className="grid gap-1.5">
            <Label>Format</Label>
            <div className="flex gap-2">
              {(["bibtex", "ris"] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFormat(f)}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${
                    format === f
                      ? "border-primary bg-accent-soft text-foreground"
                      : "border-border text-muted-foreground"
                  }`}
                >
                  {f === "bibtex" ? "BibTeX (.bib)" : "RIS (.ris)"}
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="lib-file">File</Label>
            <Input
              id="lib-file"
              type="file"
              accept={format === "ris" ? ".ris,.txt" : ".bib,.bibtex,.txt"}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
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
            <div className="grid gap-1.5">
              <Label htmlFor="proj-name">Project name</Label>
              <Input
                id="proj-name"
                value={projectName}
                placeholder="e.g. Thesis literature"
                onChange={(e) => setProjectName(e.target.value)}
              />
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={submit} disabled={busy || !file}>
            {busy ? <Loader2 className="size-4 animate-spin" /> : <FileUp className="size-4" />}
            Import
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
