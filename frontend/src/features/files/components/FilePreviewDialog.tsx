import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { UserFile } from "@/types/api";

export function FilePreviewDialog({
  file,
  onOpenChange,
}: {
  file: UserFile | null;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={!!file} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="truncate pr-8">{file?.name}</DialogTitle>
        </DialogHeader>
        {file && (
          <div className="max-h-[70vh] overflow-auto rounded-lg border border-border">
            {file.kind === "image" ? (
              <img src={`/api/files/${file.id}/raw`} alt={file.name} className="w-full object-contain" />
            ) : file.name.toLowerCase().endsWith(".pdf") ? (
              <iframe src={`/api/files/${file.id}/raw`} title={file.name} className="h-[70vh] w-full" />
            ) : (
              <div className="p-8 text-center text-sm text-muted-foreground">
                No inline preview for this file type.{" "}
                <a
                  href={`/api/files/${file.id}/raw`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary underline"
                >
                  Open in new tab
                </a>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
