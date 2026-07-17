import { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogFooter,
  DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input }    from "@/components/ui/input";
import { Label }    from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button }   from "@/components/ui/button";
import { useCreateCitation, useUpdateCitation } from "../useCitations";
import { useUI }    from "@/context/UIContext";
import { toast }    from "@/components/common/Toast";
import { cn }       from "@/lib/utils";
import type { Citation, CitationFormat } from "@/types/api";

const EMPTY = {
  title: "", authors: "", year: "", venue: "", doi: "", url: "", notes: "",
};

const FORMAT_LABELS: { key: CitationFormat; label: string }[] = [
  { key: "apa",    label: "APA 7" },
  { key: "ieee",   label: "IEEE" },
  { key: "bibtex", label: "BibTeX" },
];

/** Build a naive client-side preview (the real formatted string comes from the API after save) */
function previewFormat(form: typeof EMPTY, fmt: CitationFormat): string {
  const { title, authors, year, venue, doi, url } = form;
  if (!title && !authors) return "Fill in the fields above to see a preview.";
  if (fmt === "apa") {
    const au = authors || "Author";
    const yr = year ? `(${year})` : "";
    const vn = venue ? `*${venue}*` : "";
    const do_ = doi ? `https://doi.org/${doi}` : url;
    return [au, yr, title, vn, do_].filter(Boolean).join(". ");
  }
  if (fmt === "ieee") {
    const rawAuthors = (authors || "").split(";").map((a) => a.trim()).filter(Boolean);
    const au = rawAuthors.length <= 2 ? rawAuthors.join(" and ") : rawAuthors[0] + " et al.";
    const ti = title ? `"${title},"` : "";
    const vn = venue ? `*${venue}*,` : "";
    const yr = year ? `${year}.` : "";
    const do_ = doi ? `doi: ${doi}` : url;
    return [au, ti, vn, yr, do_].filter(Boolean).join(" ");
  }
  // BibTeX
  const first = (authors || "anon").split(";")[0].split(",")[0].trim();
  const key = first.replace(/[^a-zA-Z0-9]/g, "").toLowerCase() + (year || "");
  const fields = [
    authors  && `  author = {${authors}}`,
    title    && `  title  = {${title}}`,
    venue    && `  journal = {${venue}}`,
    year     && `  year   = {${year}}`,
    doi      && `  doi    = {${doi}}`,
    url      && `  url    = {${url}}`,
  ].filter(Boolean);
  return `@article{${key || "ref"},\n${fields.join(",\n")}\n}`;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  citation?: Citation | null;    // null = create mode
}

export function CitationFormDialog({ open, onOpenChange, citation }: Props) {
  const { currentProjectId } = useUI();
  const createCitation       = useCreateCitation();
  const updateCitation       = useUpdateCitation();

  const [form,   setForm]   = useState({ ...EMPTY });
  const [format, setFormat] = useState<CitationFormat>("apa");

  useEffect(() => {
    if (open) {
      setForm(citation ? {
        title: citation.title, authors: citation.authors, year: citation.year,
        venue: citation.venue, doi: citation.doi, url: citation.url,
        notes: citation.notes,
      } : { ...EMPTY });
    }
  }, [open, citation]);

  const set = (k: keyof typeof EMPTY) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function save() {
    if (!form.title.trim()) { toast.error("Title is required"); return; }
    try {
      if (citation) {
        await updateCitation.mutateAsync({ id: citation.id, body: form });
        toast.success("Citation updated");
      } else {
        await createCitation.mutateAsync({ ...form, project_id: currentProjectId });
        toast.success("Citation saved");
      }
      onOpenChange(false);
    } catch {
      toast.error("Could not save citation");
    }
  }

  const isBusy    = createCitation.isPending || updateCitation.isPending;
  const preview   = previewFormat(form, format);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{citation ? "Edit citation" : "Add citation"}</DialogTitle>
        </DialogHeader>

        <div className="grid gap-4">
          {/* Title */}
          <div className="grid gap-1.5">
            <Label>Title <span className="text-destructive">*</span></Label>
            <Input value={form.title} onChange={set("title")} placeholder="Paper or book title" />
          </div>

          {/* Authors */}
          <div className="grid gap-1.5">
            <Label>Authors <span className="text-muted-foreground font-normal text-xs">(Last, F.; Last, F.)</span></Label>
            <Input value={form.authors} onChange={set("authors")} placeholder="Vaswani, A.; Shazeer, N." />
          </div>

          {/* Year + Venue */}
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label>Year</Label>
              <Input value={form.year} onChange={set("year")} placeholder="2017" maxLength={4} />
            </div>
            <div className="grid gap-1.5">
              <Label>Journal / Conference</Label>
              <Input value={form.venue} onChange={set("venue")} placeholder="NeurIPS" />
            </div>
          </div>

          {/* DOI + URL */}
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label>DOI <span className="text-muted-foreground font-normal text-xs">(without https://doi.org/)</span></Label>
              <Input value={form.doi} onChange={set("doi")} placeholder="10.48550/arXiv.1706.03762" />
            </div>
            <div className="grid gap-1.5">
              <Label>URL</Label>
              <Input value={form.url} onChange={set("url")} placeholder="https://…" />
            </div>
          </div>

          {/* Notes */}
          <div className="grid gap-1.5">
            <Label>Notes <span className="text-muted-foreground font-normal text-xs">(optional)</span></Label>
            <Textarea value={form.notes} onChange={set("notes")}
              placeholder="Personal annotations, relevance notes…" rows={2} className="resize-none" />
          </div>

          {/* Format preview */}
          <div className="space-y-2">
            <div className="flex items-center gap-1 rounded-lg border border-border bg-muted/40 p-1">
              {FORMAT_LABELS.map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => setFormat(key)}
                  className={cn(
                    "flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-all",
                    format === key ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <pre className="whitespace-pre-wrap rounded-xl border border-border bg-muted/40 p-3 text-xs text-muted-foreground leading-relaxed font-mono overflow-x-auto">
              {preview}
            </pre>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={save} disabled={isBusy || !form.title.trim()}>
            {isBusy ? "Saving…" : "Save citation"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
