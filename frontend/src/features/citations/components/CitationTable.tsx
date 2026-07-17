import { Copy, Trash2, ExternalLink } from "lucide-react";
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
import type { Citation, Project } from "@/types/api";

function BibtexButton({ bibtex }: { bibtex: string }) {
  const { copy } = useClipboard();
  return (
    <button
      onClick={() => {
        copy(bibtex);
        toast.success("BibTeX copied");
      }}
      className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
      title="Copy BibTeX"
    >
      <Copy className="size-3" /> BibTeX
    </button>
  );
}

export function CitationTable({
  citations,
  projects,
  onDelete,
}: {
  citations: Citation[];
  projects: Project[];
  onDelete: (c: Citation) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Title</TableHead>
            <TableHead>Authors</TableHead>
            <TableHead>Year</TableHead>
            <TableHead>Venue</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {citations.map((c) => {
            const project = projects.find((p) => p.id === c.project_id);
            return (
              <TableRow key={c.id}>
                <TableCell className="max-w-xs">
                  <div className="flex items-center gap-1.5 font-medium">
                    <span className="truncate">{c.title || "Untitled"}</span>
                    {c.url && (
                      <a href={c.url} target="_blank" rel="noopener noreferrer" title="Open link">
                        <ExternalLink className="size-3 shrink-0 text-muted-foreground hover:text-foreground" />
                      </a>
                    )}
                  </div>
                  {project && (
                    <span className="mt-0.5 inline-block text-xs text-muted-foreground">
                      {project.emoji} {project.name}
                    </span>
                  )}
                </TableCell>
                <TableCell className="max-w-[180px] truncate text-muted-foreground">{c.authors}</TableCell>
                <TableCell className="text-muted-foreground">{c.year}</TableCell>
                <TableCell className="max-w-[160px] truncate text-muted-foreground">{c.venue}</TableCell>
                <TableCell>
                  <div className="flex items-center justify-end gap-1.5">
                    <BibtexButton bibtex={c.bibtex} />
                    <button
                      onClick={() => onDelete(c)}
                      className="rounded-md p-1.5 text-muted-foreground hover:text-destructive"
                      title="Delete"
                    >
                      <Trash2 className="size-4" />
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
