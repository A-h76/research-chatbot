import { useState } from "react";
import { Copy, Download, ExternalLink, Pencil, Plus, Quote, Search, Trash2, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { PageContainer }    from "@/components/layout/PageContainer";
import { Button }           from "@/components/ui/button";
import { EmptyState }       from "@/components/common/EmptyState";
import { ConfirmDialog }    from "@/components/common/ConfirmDialog";
import { CitationFormDialog } from "../components/CitationFormDialog";
import { useCitations, useDeleteCitation } from "../useCitations";
import { citationsApi }     from "../api";
import { useProjects }      from "@/features/projects/useProjects";
import { useUI }            from "@/context/UIContext";
import { useClipboard }     from "@/hooks/useClipboard";
import { toast }            from "@/components/common/Toast";
import { cn }               from "@/lib/utils";
import type { Citation, CitationFormat } from "@/types/api";

// ── Format selector ───────────────────────────────────────────────────────────
const FORMAT_TABS: { key: CitationFormat; label: string }[] = [
  { key: "apa",    label: "APA 7" },
  { key: "ieee",   label: "IEEE" },
  { key: "bibtex", label: "BibTeX" },
];

// ── Citation card ─────────────────────────────────────────────────────────────
function CitationCard({
  citation,
  format,
  projectName,
  onEdit,
  onDelete,
}: {
  citation: Citation;
  format: CitationFormat;
  projectName?: string;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { copy } = useClipboard();
  const [showFull, setShowFull] = useState(false);

  const formatted = citation[format] || citation.bibtex;
  const isLong    = formatted.length > 200;

  function copyFormatted() {
    copy(formatted);
    toast.success(`${format.toUpperCase()} copied`);
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.18 }}
      className="group flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 shadow-sm hover:border-primary/20 hover:shadow-md transition-all"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <h3 className="truncate text-sm font-semibold" title={citation.title}>
              {citation.title || "Untitled"}
            </h3>
            {citation.url && (
              <a href={citation.url} target="_blank" rel="noopener noreferrer"
                 title="Open URL" className="shrink-0 text-muted-foreground hover:text-primary transition-colors">
                <ExternalLink className="size-3.5" />
              </a>
            )}
          </div>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {[citation.authors?.split(";")[0]?.trim(), citation.year, citation.venue]
              .filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
          <button onClick={onEdit} title="Edit"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground">
            <Pencil className="size-3.5" />
          </button>
          <button onClick={onDelete} title="Delete"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-destructive">
            <Trash2 className="size-3.5" />
          </button>
        </div>
      </div>

      {/* Formatted citation */}
      <div className="relative rounded-lg border border-border bg-muted/30 p-3">
        <pre className={cn(
          "whitespace-pre-wrap text-[11px] leading-relaxed text-muted-foreground font-mono overflow-hidden",
          !showFull && isLong && "max-h-20",
        )}>
          {formatted}
        </pre>
        {isLong && (
          <button
            onClick={() => setShowFull(!showFull)}
            className="mt-1 text-[10px] text-primary hover:underline"
          >
            {showFull ? "Show less" : "Show more"}
          </button>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2">
        <button
          onClick={copyFormatted}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary"
        >
          <Copy className="size-3" />
          Copy {format.toUpperCase()}
        </button>
        {citation.doi && (
          <a
            href={`https://doi.org/${citation.doi}`}
            target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors"
          >
            DOI <ExternalLink className="size-3" />
          </a>
        )}
        {projectName && (
          <span className="ml-auto text-xs text-muted-foreground">
            {projectName}
          </span>
        )}
      </div>

      {citation.notes && (
        <p className="border-t border-border pt-2 text-xs italic text-muted-foreground">
          {citation.notes}
        </p>
      )}
    </motion.div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export function CitationsPage() {
  const { currentProjectId } = useUI();
  const { data: projects = [] } = useProjects();
  const deleteCitation          = useDeleteCitation();

  const [format,     setFormat]     = useState<CitationFormat>("apa");
  const [search,     setSearch]     = useState("");
  const [formOpen,   setFormOpen]   = useState(false);
  const [editing,    setEditing]    = useState<Citation | null>(null);
  const [toDelete,   setToDelete]   = useState<Citation | null>(null);
  const [projFilter, setProjFilter] = useState<number | null | "all">(
    currentProjectId ?? "all"
  );

  const listParams = {
    project_id: projFilter !== "all" ? projFilter : undefined,
    q:          search.trim() || undefined,
  };

  const { data: citations = [], isLoading } = useCitations(listParams);

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }
  function openEdit(c: Citation) {
    setEditing(c);
    setFormOpen(true);
  }

  const projectMap: Record<number, string> = {};
  for (const p of projects) projectMap[p.id] = `${p.emoji} ${p.name}`;

  const exportUrl = citationsApi.exportUrl(
    format,
    projFilter !== "all" ? projFilter : undefined,
  );

  return (
    <PageContainer
      title="Citations"
      description="Save, format, and export your references in APA, IEEE, or BibTeX."
      actions={
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-1.5">
            <Search className="size-4 shrink-0 text-muted-foreground" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search citations…"
              className="w-36 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            {search && (
              <button onClick={() => setSearch("")} className="text-muted-foreground hover:text-foreground">
                <X className="size-3.5" />
              </button>
            )}
          </div>
          <Button variant="outline" onClick={() => window.open(exportUrl, "_blank")}>
            <Download className="size-4" />
            <span className="hidden sm:inline">Export {format.toUpperCase()}</span>
          </Button>
          <Button onClick={openCreate}>
            <Plus className="size-4" /> Add
          </Button>
        </div>
      }
    >
      <div className="space-y-5">

        {/* Format tab bar */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-1 rounded-xl border border-border bg-muted/40 p-1">
            {FORMAT_TABS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setFormat(key)}
                className={cn(
                  "rounded-lg px-4 py-1.5 text-sm font-medium transition-all",
                  format === key
                    ? "bg-card shadow-sm text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Project filter */}
          {projects.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap">
              {[
                { key: "all" as const,  label: "All" },
                { key: null,            label: "Unassigned" },
                ...projects.map((p) => ({ key: p.id, label: `${p.emoji} ${p.name}` })),
              ].map(({ key, label }) => (
                <button
                  key={String(key)}
                  onClick={() => setProjFilter(key)}
                  className={cn(
                    "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                    projFilter === key
                      ? "bg-accent-soft text-primary"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Results */}
        {isLoading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-44 animate-pulse rounded-2xl bg-muted" />
            ))}
          </div>
        ) : citations.length === 0 ? (
          search || projFilter !== "all" ? (
            <EmptyState
              title="No citations match your filters"
              action={
                <Button variant="outline" size="sm"
                  onClick={() => { setSearch(""); setProjFilter("all"); }}>
                  Clear filters
                </Button>
              }
            />
          ) : (
            <EmptyState
              icon={<Quote className="size-8" />}
              title="No citations yet"
              description='Ask the AI to "save this to citations", add one manually, or use the "Save to citations" button on any paper.'
              action={<Button onClick={openCreate}><Plus className="size-4" /> Add citation</Button>}
            />
          )
        ) : (
          <>
            <p className="text-xs text-muted-foreground">
              {citations.length} citation{citations.length !== 1 ? "s" : ""}
            </p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <AnimatePresence>
                {citations.map((c) => (
                  <CitationCard
                    key={c.id}
                    citation={c}
                    format={format}
                    projectName={c.project_id ? projectMap[c.project_id] : undefined}
                    onEdit={() => openEdit(c)}
                    onDelete={() => setToDelete(c)}
                  />
                ))}
              </AnimatePresence>
            </div>
          </>
        )}
      </div>

      <CitationFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        citation={editing}
      />

      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        title="Delete this citation?"
        description="This cannot be undone."
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          if (toDelete) {
            deleteCitation.mutate(toDelete.id);
            toast.success("Citation deleted");
          }
        }}
      />
    </PageContainer>
  );
}
