import { useCallback, useRef, useState } from "react";
import { FileUp, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { DOCUMENT_ACCEPT } from "../lib/documentUpload";

export function LibraryUploadZone({
  disabled,
  onFiles,
  inputId = "library-upload-input",
  compact,
}: {
  disabled?: boolean;
  onFiles: (files: FileList | File[]) => void;
  /** Shared with page header “Upload Paper” so both open the same picker. */
  inputId?: string;
  /** Dense drop strip when Library already has papers. */
  compact?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const openPicker = () => {
    if (disabled) return;
    inputRef.current?.click();
  };

  const onDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (disabled) return;
      setDragging(true);
    },
    [disabled],
  );

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragging(false);
      if (disabled) return;
      if (e.dataTransfer.files?.length) onFiles(e.dataTransfer.files);
    },
    [disabled, onFiles],
  );

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={openPicker}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openPicker();
        }
      }}
      onDragOver={onDragOver}
      onDragEnter={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={cn(
        "rounded-lg border border-dashed text-center transition-colors",
        compact ? "px-4 py-3" : "px-6 py-8",
        dragging
          ? "border-primary bg-accent-soft/80"
          : "border-border bg-muted/20 hover:border-primary/40 hover:bg-muted/40",
        disabled && "pointer-events-none opacity-60",
      )}
    >
      <input
        id={inputId}
        ref={inputRef}
        type="file"
        className="hidden"
        accept={DOCUMENT_ACCEPT}
        multiple
        disabled={disabled}
        onChange={(e) => {
          if (e.target.files?.length) onFiles(e.target.files);
          e.target.value = "";
        }}
      />
      {compact ? (
        <div className="flex items-center justify-center gap-2 text-[13px] text-muted-foreground">
          <Upload className="size-4" />
          <span>Drop papers here, or click to upload</span>
        </div>
      ) : (
        <>
          <div className="mx-auto flex size-10 items-center justify-center rounded-lg bg-muted text-muted-foreground">
            <FileUp className="size-5" />
          </div>
          <p className="mt-3 text-sm font-medium text-foreground">
            Drop papers here, or click to browse
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            PDF, EPUB, DOCX, or TXT — multiple files supported
          </p>
          <Button
            type="button"
            size="sm"
            className="mt-4 gap-1.5"
            disabled={disabled}
            onClick={(e) => {
              e.stopPropagation();
              openPicker();
            }}
          >
            <Upload className="size-3.5" />
            Upload Paper
          </Button>
        </>
      )}
    </div>
  );
}
