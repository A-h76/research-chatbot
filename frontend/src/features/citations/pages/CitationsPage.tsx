import { useState } from "react";
import { Download, Plus, Quote, Search, X } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { CitationFormDialog } from "../components/CitationFormDialog";
import { CitationTable } from "../components/CitationTable";
import { useCitations, useDeleteCitation } from "../useCitations";
import { citationsApi } from "../api";
import { useProjects } from "@/features/projects/useProjects";
import { useUI } from "@/context/UIContext";
import { toast } from "@/components/common/Toast";
import { cn } from "@/lib/utils";
import type { Citation, CitationFormat } from "@/types/api";

const FORMAT_TABS: { key: CitationFormat; label: string }[] = [
  { key: "apa", label: "APA 7" },
  { key: "ieee", label: "IEEE" },
  { key: "bibtex", label: "BibTeX" },
];

/** D7 T4 — dense tabular citations, export-first. */
export function CitationsPage() {
  const { currentProjectId } = useUI();
  const { data: projects = [] } = useProjects();
  const deleteCitation = useDeleteCitation();

  const [format, setFormat] = useState<CitationFormat>("apa");
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Citation | null>(null);
  const [toDelete, setToDelete] = useState<Citation | null>(null);
  const [projFilter, setProjFilter] = useState<number | null | "all">(
    currentProjectId ?? "all",
  );

  const listParams = {
    project_id: projFilter !== "all" ? projFilter : undefined,
    q: search.trim() || undefined,
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

  const exportUrl = citationsApi.exportUrl(
    format,
    projFilter !== "all" ? projFilter : undefined,
  );

  return (
    <PageContainer title="Citations" dense>
      <div className="space-y-3">
        {/* Tool toolbar */}
        <div className="flex flex-wrap items-center gap-2 border-b border-border pb-3">
          <div className="flex min-w-[12rem] flex-1 items-center gap-2 rounded-md border border-border bg-card px-2.5 py-1.5">
            <Search className="size-3.5 shrink-0 text-muted-foreground" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search citations…"
              className="w-full bg-transparent text-[13px] outline-none placeholder:text-muted-foreground"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Clear"
              >
                <X className="size-3.5" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-0.5 rounded-md border border-border p-0.5">
            {FORMAT_TABS.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => setFormat(key)}
                className={cn(
                  "rounded px-2.5 py-1 text-[12px] font-medium transition-colors",
                  format === key
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {projects.length > 0 && (
            <select
              value={projFilter === "all" ? "all" : projFilter === null ? "none" : String(projFilter)}
              onChange={(e) => {
                const v = e.target.value;
                if (v === "all") setProjFilter("all");
                else if (v === "none") setProjFilter(null);
                else setProjFilter(Number(v));
              }}
              className="h-8 rounded-md border border-border bg-transparent px-2 text-[12px] outline-none"
            >
              <option value="all">All projects</option>
              <option value="none">Unassigned</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.emoji} {p.name}
                </option>
              ))}
            </select>
          )}

          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 text-[12px]"
            onClick={() => window.open(exportUrl, "_blank")}
          >
            <Download className="size-3.5" />
            Export {format.toUpperCase()}
          </Button>
          <Button size="sm" className="h-8 gap-1.5 text-[12px]" onClick={openCreate}>
            <Plus className="size-3.5" /> Add
          </Button>
        </div>

        {isLoading ? (
          <div className="h-40 animate-pulse rounded-lg bg-muted/40" />
        ) : citations.length === 0 ? (
          search || projFilter !== "all" ? (
            <EmptyState
              title="No citations match"
              action={
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSearch("");
                    setProjFilter("all");
                  }}
                >
                  Clear filters
                </Button>
              }
            />
          ) : (
            <EmptyState
              icon={<Quote className="size-7" />}
              title="No citations yet"
              description="Save from a paper workspace, or add one manually."
              action={
                <Button size="sm" onClick={openCreate}>
                  <Plus className="size-3.5" /> Add citation
                </Button>
              }
            />
          )
        ) : (
          <>
            <p className="text-[12px] text-muted-foreground">
              {citations.length} citation{citations.length !== 1 ? "s" : ""} · {format.toUpperCase()}
            </p>
            <CitationTable
              citations={citations}
              projects={projects}
              format={format}
              onEdit={openEdit}
              onDelete={setToDelete}
            />
          </>
        )}
      </div>

      <CitationFormDialog open={formOpen} onOpenChange={setFormOpen} citation={editing} />

      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        title="Delete this citation?"
        entityName={
          toDelete
            ? [toDelete.title, toDelete.authors].filter(Boolean).join(" — ") || null
            : null
        }
        description="This citation will be removed from your library export list."
        confirmLabel="Delete citation"
        cancelLabel="Keep"
        destructive
        onConfirm={async () => {
          if (!toDelete) return;
          await deleteCitation.mutateAsync(toDelete.id);
          toast.success("Citation deleted");
          setToDelete(null);
        }}
      />
    </PageContainer>
  );
}
