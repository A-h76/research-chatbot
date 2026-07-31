import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  disabled?: boolean;
  onFiles: (files: FileList | File[]) => void;
  uploadItems: LibraryUploadItem[];
  onClearFinished: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload papers</DialogTitle>
          <DialogDescription>
            Drop PDFs here or browse. They’ll appear in your library and start processing.
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
      </DialogContent>
    </Dialog>
  );
}
