import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileUp, Hash, Link2, Upload } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/common/Toast";
import { useLibraryUpload } from "@/features/files/hooks/useLibraryUpload";
import { DOCUMENT_ACCEPT } from "@/features/files/lib/documentUpload";
import { cn } from "@/lib/utils";

export function HomeHeroUpload() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const { upload, isUploading } = useLibraryUpload();
  const [dragging, setDragging] = useState(false);

  const onFiles = useCallback(
    async (files: FileList | File[]) => {
      await upload(files);
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Upload started — opening Library");
      navigate("/library");
    },
    [upload, qc, navigate],
  );

  return (
    <div
      className={cn(
        "rounded-xl bg-primary p-5 text-primary-foreground shadow-sm sm:p-6",
        "transition-[box-shadow,transform] duration-150 ease-out",
        "hover:shadow-md hover:-translate-y-0.5",
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary-foreground/15">
          <Upload className="size-4" aria-hidden />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-[16px] font-semibold tracking-tight sm:text-[17px]">
            Upload your first paper
          </h2>
          <p className="mt-1 text-[13px] text-primary-foreground/85">
            Start your evidence pipeline.
          </p>
        </div>
      </div>

      <div
        role="button"
        tabIndex={0}
        aria-label="Drop PDF to upload"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragEnter={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (e.dataTransfer.files?.length) void onFiles(e.dataTransfer.files);
        }}
        className={cn(
          "mt-4 cursor-pointer rounded-lg border border-dashed px-4 py-5 text-center transition-colors duration-150",
          dragging
            ? "border-primary-foreground bg-primary-foreground/15"
            : "border-primary-foreground/35 bg-primary-foreground/8 hover:bg-primary-foreground/12",
        )}
      >
        <FileUp className="mx-auto size-4 opacity-90" aria-hidden />
        <p className="mt-2 text-[13px] font-medium">
          {isUploading ? "Uploading…" : "Drag & drop a PDF here"}
        </p>
        <p className="mt-0.5 text-[12px] text-primary-foreground/75">or click to browse</p>
      </div>

      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept={DOCUMENT_ACCEPT}
        multiple
        disabled={isUploading}
        onChange={(e) => {
          if (e.target.files?.length) void onFiles(e.target.files);
          e.target.value = "";
        }}
      />

      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          className="h-8 bg-primary-foreground text-primary hover:bg-primary-foreground/90"
          disabled={isUploading}
          onClick={() => inputRef.current?.click()}
        >
          <Upload className="size-3.5" />
          Import PDF
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-8 text-primary-foreground hover:bg-primary-foreground/15 hover:text-primary-foreground"
          onClick={() => navigate("/search?mode=discover&q=10.")}
        >
          <Link2 className="size-3.5" />
          Import DOI
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-8 text-primary-foreground hover:bg-primary-foreground/15 hover:text-primary-foreground"
          onClick={() => navigate("/search?mode=discover&provider=arxiv")}
        >
          <Hash className="size-3.5" />
          Import arXiv
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-8 text-primary-foreground hover:bg-primary-foreground/15 hover:text-primary-foreground"
          onClick={() => navigate("/search?mode=discover&provider=europe_pmc")}
        >
          <Hash className="size-3.5" />
          Import Europe PMC
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-8 text-primary-foreground hover:bg-primary-foreground/15 hover:text-primary-foreground"
          onClick={() => navigate("/search?mode=discover&provider=orcid")}
        >
          <Hash className="size-3.5" />
          Import ORCID
        </Button>
      </div>
    </div>
  );
}
