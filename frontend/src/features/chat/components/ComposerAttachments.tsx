import { FileText, ImageIcon, Loader2, X } from "lucide-react";
import type { PendingFile } from "../types";

export function ComposerAttachments({
  files,
  onRemove,
}: {
  files: PendingFile[];
  onRemove: (id: number) => void;
}) {
  if (!files.length) return null;
  return (
    <div className="mb-2 flex flex-wrap gap-1.5">
      {files.map((f) => (
        <div
          key={f.id}
          className="flex max-w-[230px] items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs"
        >
          {f.uploading ? (
            <Loader2 className="size-3.5 shrink-0 animate-spin text-muted-foreground" />
          ) : f.kind === "image" ? (
            <ImageIcon className="size-3.5 shrink-0 text-muted-foreground" />
          ) : (
            <FileText className="size-3.5 shrink-0 text-muted-foreground" />
          )}
          <span className="truncate">{f.name}</span>
          {!f.uploading && (
            <button
              onClick={() => onRemove(f.id)}
              className="text-muted-foreground hover:text-destructive"
              title="Remove"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
