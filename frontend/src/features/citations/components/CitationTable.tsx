import { Copy, Trash2, ExternalLink, Pencil, CircleDashed, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
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
import { citationsApi } from "../api";
import { CrossrefIcon } from "@/features/sidebar/components/BrandIcons";

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

function FormattedCitationCell({
  citation,
  format,
}: {
  citation: Citation;
  format: CitationFormat;
}) {
  const local = citation[format] || citation.bibtex || "";
  const { data, isLoading } = useQuery({
    queryKey: ["citation-format", citation.id, format],
    queryFn: () => citationsApi.format(citation.id, format),
    enabled: Boolean(citation.doi),
    staleTime: 7 * 24 * 60 * 60 * 1000,
    retry: 1,
  });

  const text = data?.citation || local;
  const verified = Boolean(data?.verified);
  const showBadge = Boolean(citation.doi) || Boolean(local);

  return (
    <div className="space-y-1.5">
      {showBadge && (
        <span
          className={
            verified
              ? "inline-flex items-center gap-1 rounded border border-sem-ready/35 bg-sem-ready/10 px-1.5 py-0.5 text-[10px] text-sem-ready"
              : "inline-flex items-center gap-1 rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground"
          }
          title={
            verified
              ? "Formatted from Crossref metadata"
              : citation.doi
                ? "Locally formatted — Crossref not verified yet"
                : "No DOI — locally formatted"
          }
        >
          {isLoading ? (
            <Loader2 className="size-3 animate-spin" />
          ) : verified ? (
            <CrossrefIcon className="size-3" />
          ) : (
            <CircleDashed className="size-3" />
          )}
          {isLoading ? "Checking…" : verified ? "Verified · Crossref" : "~ AI formatted"}
        </span>
      )}
      <pre className="line-clamp-3 whitespace-pre-wrap font-mono text-[11px] leading-snug text-muted-foreground">
        {text || "—"}
      </pre>
      {text && (
        <CopyFormatButton label={format.toUpperCase()} text={text} />
      )}
    </div>
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
    <div className="overflow-x-auto rounded-md border border-border" data-density="high">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="h-8 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Title
            </TableHead>
            <TableHead className="h-8 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Authors
            </TableHead>
            <TableHead className="h-8 w-16 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Year
            </TableHead>
            <TableHead className="h-8 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Venue
            </TableHead>
            <TableHead className="h-8 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Formatted
            </TableHead>
            <TableHead className="h-8 text-right text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Actions
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {citations.map((c) => {
            const project = projects.find((p) => p.id === c.project_id);
            return (
              <TableRow key={c.id} className="group">
                <TableCell className="max-w-[14rem] py-2 align-top">
                  <div className="flex items-start gap-1.5 text-[13px] font-medium">
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
                      className="mt-0.5 block font-mono text-[11px] text-muted-foreground hover:text-primary"
                    >
                      DOI
                    </a>
                  )}
                </TableCell>
                <TableCell className="max-w-[10rem] truncate py-2 align-top text-[12px] text-muted-foreground">
                  {c.authors || "—"}
                </TableCell>
                <TableCell className="py-2 align-top text-[12px] tabular-nums text-muted-foreground">
                  {c.year || "—"}
                </TableCell>
                <TableCell className="max-w-[9rem] truncate py-2 align-top text-[12px] text-muted-foreground">
                  {c.venue || "—"}
                </TableCell>
                <TableCell className="max-w-[16rem] py-2 align-top">
                  <FormattedCitationCell citation={c} format={format} />
                </TableCell>
                <TableCell className="py-2 align-top">
                  <div className="flex flex-wrap items-center justify-end gap-1">
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
