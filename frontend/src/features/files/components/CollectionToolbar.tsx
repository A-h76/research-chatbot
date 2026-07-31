import { useNavigate } from "react-router-dom";
import {
  Search,
  GitCompare,
  Quote,
  SlidersHorizontal,
  Upload,
  X,
  Wand2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { LibraryImportMenu } from "./LibraryImportMenu";
import { cn } from "@/lib/utils";

/**
 * Library CollectionToolbar — search primary, one teal Upload, Import menu.
 * Secondary actions stay ghost/outline (PR1 hierarchy).
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
  className?: string;
}) {
  const navigate = useNavigate();

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2",
        className,
      )}
    >
      <div className="flex min-w-[12rem] flex-1 items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <Search className="size-3.5 shrink-0 text-muted-foreground" />
        <input
          value={q}
          onChange={(e) => onQChange(e.target.value)}
          placeholder="Search papers, authors, DOI, venue…"
          className="w-full bg-transparent text-[13px] outline-none placeholder:text-muted-foreground"
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
        className="h-8 gap-1.5 text-[12px] text-muted-foreground"
        onClick={() => navigate("/research/compare?tab=matrix")}
      >
        <GitCompare className="size-3.5" />
        Compare
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-8 gap-1.5 text-[12px] text-muted-foreground"
        onClick={() => navigate("/citations")}
      >
        <Quote className="size-3.5" />
        Citations
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-8 gap-1.5 text-[12px] text-muted-foreground"
        onClick={() => navigate("/writing")}
      >
        <Wand2 className="size-3.5" />
        Writing
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className={cn(
          "h-8 gap-1.5 text-[12px]",
          showFilters
            ? "bg-muted text-foreground"
            : "text-muted-foreground",
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
  );
}
