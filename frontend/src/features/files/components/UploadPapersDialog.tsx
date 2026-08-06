import { Link } from "react-router-dom";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LibraryUploadZone } from "./LibraryUploadZone";
import { LibraryUploadQueue } from "./LibraryUploadQueue";
import type { LibraryUploadItem } from "../hooks/useLibraryUpload";

export function UploadPapersDialog({
  open,
  onOpenChange,
  disabled,
  onFiles,
  uploadItems,
  onClearFinished,
  projectId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  disabled?: boolean;
  onFiles: (files: FileList | File[]) => void;
  uploadItems: LibraryUploadItem[];
  onClearFinished: () => void;
  /** When set, next-step copy is project-scoped. */
  projectId?: number | null;
}) {
  const uploaded = uploadItems.filter((i) => i.status === "uploaded" && i.fileId != null);
  const failed = uploadItems.filter((i) => i.status === "failed");
  const inFlight = uploadItems.filter((i) => i.status === "uploading");
  const firstId = uploaded[0]?.fileId ?? null;
  const showNext = uploaded.length > 0 && inFlight.length === 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload papers</DialogTitle>
          <DialogDescription>
            Drop PDFs here or browse. They’ll appear in your{" "}
            {projectId != null ? "project" : "library"} and start processing.
          </DialogDescription>
        </DialogHeader>
        <LibraryUploadZone
          disabled={disabled}
          onFiles={(f) => {
            onFiles(f);
          }}
          inputId="library-upload-modal-input"
          compact={false}
        />
        {uploadItems.length > 0 && (
          <LibraryUploadQueue items={uploadItems} onClearFinished={onClearFinished} />
        )}

        {showNext && (
          <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-3">
            <div>
              <p className="text-sm font-medium text-foreground">
                {uploaded.length} paper{uploaded.length === 1 ? "" : "s"} uploaded
                {failed.length > 0 ? ` · ${failed.length} failed` : ""}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Processing runs in the background. Next recommended step:
              </p>
            </div>
            <ol className="list-decimal space-y-1 pl-4 text-xs text-muted-foreground">
              <li>Open a paper and watch status until Chat Ready</li>
              <li>Review Research Profile / Structure</li>
              <li>Ask Dhund or extract Evidence</li>
            </ol>
            <div className="flex flex-wrap gap-2">
              {firstId != null && (
                <Link
                  to={`/papers/${firstId}`}
                  onClick={() => onOpenChange(false)}
                  className={cn(buttonVariants({ size: "sm" }))}
                >
                  Open first paper
                </Link>
              )}
              {projectId != null && (
                <Link
                  to={`/projects/${projectId}`}
                  onClick={() => onOpenChange(false)}
                  className={cn(buttonVariants({ size: "sm", variant: "outline" }))}
                >
                  Back to project
                </Link>
              )}
              <Button size="sm" variant="ghost" onClick={() => onOpenChange(false)}>
                Done
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
