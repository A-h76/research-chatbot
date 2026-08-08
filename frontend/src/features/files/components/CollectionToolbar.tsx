import {

  Search,

  SlidersHorizontal,

  X,

  GitCompare,

  MessageSquare,

  FolderPlus,

  FolderMinus,

} from "lucide-react";

import { Button } from "@/components/ui/button";

import { cn } from "@/lib/utils";



/**

 * Library list toolbar — search + filters + bulk actions.

 * Import lives on the page header (Constitution: one primary action).

 */

export function CollectionToolbar({

  q,

  onQChange,

  showFilters,

  onToggleFilters,

  selectedCount = 0,

  onClearSelection,

  onBulkCompare,

  onBulkAsk,

  onBulkAddToCollection,

  onBulkRemoveFromCollection,

  needPdfFilter = false,

  onClearNeedPdf,

  className,

}: {

  q: string;

  onQChange: (v: string) => void;

  showFilters: boolean;

  onToggleFilters: () => void;

  selectedCount?: number;

  onClearSelection?: () => void;

  onBulkCompare?: () => void;

  onBulkAsk?: () => void;

  onBulkAddToCollection?: () => void;

  onBulkRemoveFromCollection?: () => void;

  needPdfFilter?: boolean;

  onClearNeedPdf?: () => void;

  className?: string;

}) {

  const hasSelection = selectedCount > 0;



  return (

    <div className={cn("space-y-3", className)}>

      <div className="flex flex-wrap items-center gap-2">

        <div className="flex min-w-[14rem] flex-1 items-center gap-2 border-b border-border px-1 py-2">

          <Search className="size-3.5 shrink-0 text-text-tertiary" />

          <input

            value={q}

            onChange={(e) => onQChange(e.target.value)}

            placeholder="Search papers…"

            className="w-full bg-transparent text-[13px] outline-none placeholder:text-text-tertiary"

            aria-label="Search library"

          />

          {q && (

            <button

              type="button"

              onClick={() => onQChange("")}

              className="text-text-tertiary hover:text-text-primary"

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

            showFilters ? "bg-muted text-text-primary" : "text-text-tertiary",

          )}

          onClick={onToggleFilters}

        >

          <SlidersHorizontal className="size-3.5" />

          Filters

        </Button>

      </div>



      {needPdfFilter ? (

        <div className="flex flex-wrap items-center gap-2 text-[12px]">

          <span className="rounded border border-amber-600/40 bg-amber-500/5 px-2 py-1 text-amber-900 dark:text-amber-100">

            Showing papers that need a PDF

          </span>

          <button

            type="button"

            className="text-text-tertiary hover:text-text-primary"

            onClick={onClearNeedPdf}

          >

            Clear

          </button>

        </div>

      ) : null}



      {hasSelection && (

        <div className="flex flex-wrap items-center gap-2 rounded-md bg-muted/40 px-3 py-2">

          <span className="text-[12px] font-medium tabular-nums text-text-primary">

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

          {onBulkRemoveFromCollection ? (

            <Button

              variant="ghost"

              size="sm"

              className="h-7 gap-1.5 text-[12px]"

              onClick={onBulkRemoveFromCollection}

            >

              <FolderMinus className="size-3.5" />

              Remove from collection

            </Button>

          ) : null}

          <button

            type="button"

            className="ml-auto text-[12px] text-text-tertiary hover:text-text-primary"

            onClick={onClearSelection}

          >

            Clear

          </button>

        </div>

      )}

    </div>

  );

}


