import { Copy, Trash2, ExternalLink, Pencil } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useClipboard } from "@/hooks/useClipboard";
import { toast } from "@/components/common/Toast";
import type { Citation, CitationFormat, Project } from "@/types/api";

function CopyFormatButton({
  label,
  text,
}: {
  label: string;
  text: string;
}) {
  const { copy } = useClipboard();
  return (
    <button
      type="button"
      onClick={() => {
        copy(text);
        toast.success(`${label} copied`);
      }}
      className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground"
      title={`Copy ${label}`}
    >
      <Copy className="size-3" /> {label}
    </button>
  );
}

/** D7 T4 — dense citation table (export-first). */
export function CitationTable({
  citations,
  projects,
  format,
  onEdit,
  onDelete,
}: {
  citations: Citation[];
  projects: Project[];
  format: CitationFormat;
  onEdit: (c: Citation) => void;
  onDelete: (c: Citation) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="h-9 text-[12px]">Title</TableHead>
            <TableHead className="h-9 text-[12px]">Authors</TableHead>
            <TableHead className="h-9 w-16 text-[12px]">Year</TableHead>
            <TableHead className="h-9 text-[12px]">Venue</TableHead>
            <TableHead className="h-9 text-[12px]">Formatted</TableHead>
            <TableHead className="h-9 text-right text-[12px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {citations.map((c) => {
            const project = projects.find((p) => p.id === c.project_id);
            const formatted = c[format] || c.bibtex;
            return (
              <TableRow key={c.id} className="group">
                <TableCell className="max-w-[14rem] py-2.5 align-top">
                  <div className="flex items-start gap-1.5 font-medium text-[13px]">
                    <span className="line-clamp-2">{c.title || "Untitled"}</span>
                    {c.url && (
                      <a
                        href={c.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Open link"
                        className="mt-0.5 shrink-0"
                      >
                        <ExternalLink className="size-3 text-muted-foreground hover:text-foreground" />
                      </a>
                    )}
                  </div>
                  {project && (
                    <span className="mt-0.5 inline-block text-[11px] text-muted-foreground">
                      {project.emoji} {project.name}
                    </span>
                  )}
                  {c.doi && (
                    <a
                      href={`https://doi.org/${c.doi}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-0.5 block text-[11px] text-muted-foreground hover:text-primary"
                    >
                      DOI
                    </a>
                  )}
                </TableCell>
                <TableCell className="max-w-[10rem] truncate py-2.5 text-[12px] text-muted-foreground align-top">
                  {c.authors || "—"}
                </TableCell>
                <TableCell className="py-2.5 text-[12px] text-muted-foreground align-top">
                  {c.year || "—"}
                </TableCell>
                <TableCell className="max-w-[9rem] truncate py-2.5 text-[12px] text-muted-foreground align-top">
                  {c.venue || "—"}
                </TableCell>
                <TableCell className="max-w-[16rem] py-2.5 align-top">
                  <pre className="line-clamp-3 whitespace-pre-wrap font-mono text-[11px] leading-snug text-muted-foreground">
                    {formatted}
                  </pre>
                </TableCell>
                <TableCell className="py-2.5 align-top">
                  <div className="flex flex-wrap items-center justify-end gap-1">
                    <CopyFormatButton
                      label={format.toUpperCase()}
                      text={formatted}
                    />
                    <button
                      type="button"
                      onClick={() => onEdit(c)}
                      className="rounded-md p-1.5 text-muted-foreground opacity-0 hover:text-foreground group-hover:opacity-100 focus:opacity-100"
                      title="Edit"
                    >
                      <Pencil className="size-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(c)}
                      className="rounded-md p-1.5 text-muted-foreground opacity-0 hover:text-destructive group-hover:opacity-100 focus:opacity-100"
                      title="Delete"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
