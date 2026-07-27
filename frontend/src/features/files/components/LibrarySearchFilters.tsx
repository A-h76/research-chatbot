import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { LibraryFacets, LibraryListParams } from "../api";

export type LibraryFilterState = Pick<
  LibraryListParams,
  | "author"
  | "doi"
  | "year"
  | "year_from"
  | "year_to"
  | "venue"
  | "import_source"
  | "recent_days"
  | "tag"
>;

const SOURCE_OPTIONS: { value: NonNullable<LibraryListParams["import_source"]>; label: string }[] = [
  { value: "zotero", label: "From Zotero" },
  { value: "bibtex", label: "BibTeX import" },
  { value: "ris", label: "RIS import" },
  { value: "discover", label: "OpenAlex / Discover" },
  { value: "upload", label: "Uploaded PDF" },
];

export function LibrarySearchFilters({
  filters,
  onChange,
  facets,
  tagList,
  onClear,
  className,
}: {
  filters: LibraryFilterState;
  onChange: (patch: Partial<LibraryFilterState>) => void;
  facets?: LibraryFacets;
  tagList: { tag: string; count: number }[];
  onClear: () => void;
  className?: string;
}) {
  const activeTags = filters.tag ?? [];
  const importSource = filters.import_source;

  return (
    <div className={cn("rounded-lg border border-border bg-card p-4 space-y-4", className)}>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="grid gap-1.5">
          <Label htmlFor="f-author" className="text-xs">
            Author
          </Label>
          <Input
            id="f-author"
            value={filters.author ?? ""}
            placeholder="Last name…"
            className="h-8 text-sm"
            onChange={(e) => onChange({ author: e.target.value || undefined })}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="f-doi" className="text-xs">
            DOI
          </Label>
          <Input
            id="f-doi"
            value={filters.doi ?? ""}
            placeholder="10.1234/…"
            className="h-8 text-sm"
            onChange={(e) => onChange({ doi: e.target.value || undefined })}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="f-year" className="text-xs">
            Year
          </Label>
          <Input
            id="f-year"
            value={filters.year ?? ""}
            placeholder="2024"
            className="h-8 text-sm"
            onChange={(e) => onChange({ year: e.target.value || undefined })}
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="f-venue" className="text-xs">
            Journal / venue
          </Label>
          <Input
            id="f-venue"
            value={filters.venue ?? ""}
            placeholder="NeurIPS, Nature…"
            className="h-8 text-sm"
            onChange={(e) => onChange({ venue: e.target.value || undefined })}
          />
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium text-muted-foreground">Source</p>
        <div className="flex flex-wrap gap-1.5">
          {SOURCE_OPTIONS.map(({ value, label }) => {
            const count = facets?.import_source?.[value];
            const active = importSource === value;
            return (
              <button
                key={value}
                type="button"
                onClick={() => onChange({ import_source: active ? undefined : value })}
                className={cn(
                  "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs transition-colors",
                  active
                    ? "border-primary bg-accent-soft text-primary"
                    : "border-border text-muted-foreground hover:border-primary/40 hover:text-foreground",
                )}
              >
                {label}
                {count != null && count > 0 && (
                  <span className="text-[10px] opacity-70">{count}</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {(facets?.years?.length ?? 0) > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium text-muted-foreground">Year</p>
          <div className="flex flex-wrap gap-1.5">
            {facets!.years.slice(0, 8).map(({ year, count }) => (
              <button
                key={year}
                type="button"
                onClick={() => onChange({ year: filters.year === year ? undefined : year })}
                className={cn(
                  "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs transition-colors",
                  filters.year === year
                    ? "border-primary bg-accent-soft text-primary"
                    : "border-border text-muted-foreground hover:border-primary/40",
                )}
              >
                {year}
                <span className="text-[10px] opacity-70">{count}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {tagList.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium text-muted-foreground">Tags</p>
          <div className="flex flex-wrap gap-1.5">
            {tagList.map(({ tag, count }) => (
              <button
                key={tag}
                type="button"
                onClick={() => {
                  const next = activeTags.includes(tag)
                    ? activeTags.filter((t) => t !== tag)
                    : [...activeTags, tag];
                  onChange({ tag: next.length ? next : undefined });
                }}
                className={cn(
                  "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs transition-colors",
                  activeTags.includes(tag)
                    ? "border-primary bg-accent-soft text-primary"
                    : "border-border text-muted-foreground hover:border-primary/40",
                )}
              >
                {tag}
                <span className="text-[10px] opacity-70">{count}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() =>
            onChange({ recent_days: filters.recent_days === 7 ? undefined : 7 })
          }
          className={cn(
            "rounded-md border px-2 py-0.5 text-xs",
            filters.recent_days === 7
              ? "border-primary bg-accent-soft text-primary"
              : "border-border text-muted-foreground",
          )}
        >
          Recently added (7d)
        </button>
        <button
          type="button"
          onClick={onClear}
          className="text-xs text-muted-foreground underline-offset-2 hover:underline"
        >
          Clear all filters
        </button>
      </div>
    </div>
  );
}
