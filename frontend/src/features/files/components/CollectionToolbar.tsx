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
import { cn } from "@/lib/utils";

/**
 * D5/D7 — Library CollectionToolbar (T1).
 * Search · Compare · Citations · Writing · Filters · Upload
 */
export function CollectionToolbar({
  q,
  onQChange,
  showFilters,
  onToggleFilters,
  isUploading,
  uploadInputId = "library-upload-input",
  className,
}: {
  q: string;
  onQChange: (v: string) => void;
  showFilters: boolean;
  onToggleFilters: () => void;
  isUploading?: boolean;
  uploadInputId?: string;
  className?: string;
}) {
  const navigate = useNavigate();

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 border-b border-border pb-3",
        className,
      )}
    >
      <div className="flex min-w-[12rem] flex-1 items-center gap-2 rounded-md border border-border bg-card px-2.5 py-1.5">
        <Search className="size-3.5 shrink-0 text-muted-foreground" />
        <input
          value={q}
          onChange={(e) => onQChange(e.target.value)}
          placeholder="Search title, author, DOI, venue… (doi:10.x author:smith)"
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
        variant="outline"
        size="sm"
        className="h-8 gap-1.5 text-[12px]"
        onClick={() => navigate("/research/compare")}
      >
        <GitCompare className="size-3.5" />
        Compare
      </Button>
      <Button
        variant="outline"
        size="sm"
        className="h-8 gap-1.5 text-[12px]"
        onClick={() => navigate("/citations")}
      >
        <Quote className="size-3.5" />
        Citations
      </Button>
      <Button
        variant="outline"
        size="sm"
        className="h-8 gap-1.5 text-[12px]"
        onClick={() => navigate("/writing")}
      >
        <Wand2 className="size-3.5" />
        Writing
      </Button>
      <Button
        variant="outline"
        size="sm"
        className={cn(
          "h-8 gap-1.5 text-[12px]",
          showFilters && "border-primary/40 bg-accent-soft text-primary",
        )}
        onClick={onToggleFilters}
      >
        <SlidersHorizontal className="size-3.5" />
        Filters
      </Button>
      <Button
        size="sm"
        className="h-8 gap-1.5 text-[12px]"
        disabled={isUploading}
        onClick={() => {
          const input = document.getElementById(uploadInputId) as HTMLInputElement | null;
          input?.click();
        }}
      >
        <Upload className="size-3.5" />
        Upload
      </Button>
    </div>
  );
}
