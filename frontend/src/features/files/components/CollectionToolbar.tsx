import {
  Search,
  SlidersHorizontal,
  Upload,
  X,
  GitCompare,
  MessageSquare,
  FolderPlus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { LibraryImportMenu } from "./LibraryImportMenu";
import { cn } from "@/lib/utils";

/**
 * Library toolbar — global search + Upload/Import.
 * Compare / Ask appear only when papers are selected (bulk bar).
 */
export function CollectionToolbar({
  q,
  onQChange,
  showFilters,
  onToggleFilters,
  isUploading,
  onUpload,
  onBibtex,
  onZoteroImport,
  onMendeleyImport,
  selectedCount = 0,
  onClearSelection,
  onBulkCompare,
  onBulkAsk,
  onBulkAddToCollection,
  className,
}: {
  q: string;
  onQChange: (v: string) => void;
  showFilters: boolean;
  onToggleFilters: () => void;
  isUploading?: boolean;
  onUpload: () => void;
  onBibtex: () => void;
  onZoteroImport?: () => void;
  onMendeleyImport?: () => void;
  selectedCount?: number;
  onClearSelection?: () => void;
  onBulkCompare?: () => void;
  onBulkAsk?: () => void;
  onBulkAddToCollection?: () => void;
  className?: string;
}) {
  const hasSelection = selectedCount > 0;

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex min-w-[14rem] flex-1 items-center gap-2 border-b border-border px-1 py-2">
          <Search className="size-3.5 shrink-0 text-muted-foreground" />
          <input
            value={q}
            onChange={(e) => onQChange(e.target.value)}
            placeholder="Search papers, authors, DOI, PMID, claims…"
            className="w-full bg-transparent text-[13px] outline-none placeholder:text-muted-foreground/80"
            aria-label="Search library"
          />
          {q && (
            <button
              type="button"
              onClick={() => onQChange("")}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Clear search"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>

        <Button
          variant="ghost"
          size="sm"
          className={cn(
            "h-8 gap-1.5 text-[12px]",
            showFilters ? "bg-muted text-foreground" : "text-muted-foreground",
          )}
          onClick={onToggleFilters}
        >
          <SlidersHorizontal className="size-3.5" />
          Filters
        </Button>
        <LibraryImportMenu
          onUpload={onUpload}
          onBibtex={onBibtex}
          onZoteroImport={onZoteroImport}
          onMendeleyImport={onMendeleyImport}
        />
        <Button
          size="sm"
          className="h-8 gap-1.5 text-[12px]"
          disabled={isUploading}
          onClick={onUpload}
        >
          <Upload className="size-3.5" />
          Upload
        </Button>
      </div>

      {hasSelection && (
        <div className="flex flex-wrap items-center gap-2 rounded-md bg-muted/40 px-3 py-2">
          <span className="text-[12px] font-medium tabular-nums text-foreground">
            {selectedCount} selected
          </span>
          <div className="mx-1 h-4 w-px bg-border" />
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1.5 text-[12px]"
            onClick={onBulkAsk}
          >
            <MessageSquare className="size-3.5" />
            Ask Dhund
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1.5 text-[12px]"
            disabled={selectedCount < 2}
            onClick={onBulkCompare}
            title={selectedCount < 2 ? "Select at least two papers" : "Compare selected"}
          >
            <GitCompare className="size-3.5" />
            Compare
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1.5 text-[12px]"
            onClick={onBulkAddToCollection}
          >
            <FolderPlus className="size-3.5" />
            Add to collection
          </Button>
          <button
            type="button"
            className="ml-auto text-[12px] text-muted-foreground hover:text-foreground"
            onClick={onClearSelection}
          >
            Clear
          </button>
        </div>
      )}
    </div>
  );
}
