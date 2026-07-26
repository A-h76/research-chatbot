import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Wand2, Loader2, Copy, Download, RefreshCw,
  BookOpen, GraduationCap, Minimize2, Maximize2,
  AlignLeft, FileText, MessageSquare, StickyNote, AlertTriangle,
  Quote,
} from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useFiles } from "@/features/files/useFiles";
import { useNotes } from "@/features/notes/useNotes";
import { useConversations } from "@/features/chat/hooks/useConversation";
import { useUI } from "@/context/UIContext";
import { useClipboard } from "@/hooks/useClipboard";
import { writingApi } from "../api";
import { toast } from "@/components/common/Toast";
import { cn } from "@/lib/utils";
import type { WritingAction } from "@/types/api";

const ACTIONS: { key: WritingAction; label: string; icon: React.ReactNode; desc: string }[] = [
  { key: "rewrite_academic", label: "Academic", icon: <GraduationCap className="size-3.5" />, desc: "Formal academic register" },
  { key: "improve_grammar", label: "Grammar", icon: <AlignLeft className="size-3.5" />, desc: "Correct errors" },
  { key: "improve_clarity", label: "Clarity", icon: <BookOpen className="size-3.5" />, desc: "Clearer prose" },
  { key: "expand", label: "Expand", icon: <Maximize2 className="size-3.5" />, desc: "Add detail" },
  { key: "shorten", label: "Shorten", icon: <Minimize2 className="size-3.5" />, desc: "Cut filler" },
  { key: "generate_abstract", label: "Abstract", icon: <FileText className="size-3.5" />, desc: "Structured abstract" },
  { key: "improve_conclusion", label: "Conclusion", icon: <Wand2 className="size-3.5" />, desc: "Strengthen ending" },
];

function DraftTab() {
  const { copy } = useClipboard();
  const [input, setInput] = useState("");
  const [result, setResult] = useState("");
  const [warning, setWarning] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<WritingAction | null>(null);

  async function run(action: WritingAction) {
    if (!input.trim()) {
      toast.error("Paste some text first.");
      return;
    }
    setLoading(true);
    setActiveAction(action);
    try {
      const res = await fetch("/api/writing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, text: input }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.error || "Failed");
      setResult(data.result);
      setWarning(data.warning || "");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Writing assistant failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      {/* Action toolbar — not marketing cards */}
      <div className="flex flex-wrap items-center gap-1.5 border-b border-border pb-3">
        <span className="mr-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Transform
        </span>
        {ACTIONS.map(({ key, label, icon, desc }) => (
          <button
            key={key}
            type="button"
            onClick={() => run(key)}
            disabled={loading}
            title={desc}
            className={cn(
              "inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-[12px] font-medium transition-colors",
              loading && activeAction === key
                ? "border-primary bg-accent-soft text-primary"
                : "border-border bg-card text-foreground hover:bg-muted/50",
              loading && activeAction !== key && "opacity-50",
            )}
          >
            {loading && activeAction === key ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <span className="text-muted-foreground">{icon}</span>
            )}
            {label}
          </button>
        ))}
        <span className="ml-auto hidden text-[11px] text-muted-foreground sm:inline">
          Does not invent citations or data
        </span>
      </div>

      <div className="grid min-h-0 gap-3 lg:grid-cols-2">
        <div className="flex min-h-0 flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <p className="text-[12px] font-medium text-muted-foreground">Draft</p>
            {input && (
              <span className="text-[11px] tabular-nums text-muted-foreground">{input.length}</span>
            )}
          </div>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Paste a paragraph, section, or abstract…"
            rows={16}
            className="min-h-[18rem] w-full flex-1 resize-y rounded-lg border border-border bg-card px-3 py-2.5 text-[13px] leading-relaxed outline-none focus:border-ring focus:ring-2 focus:ring-ring/20 placeholder:text-muted-foreground/60"
          />
        </div>

        <div className="flex min-h-0 flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <p className="text-[12px] font-medium text-muted-foreground">Output</p>
            {result && (
              <div className="flex items-center gap-1">
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 gap-1 text-[11px]"
                  onClick={() => {
                    setInput(result);
                    setResult("");
                    toast.success("Moved to draft");
                  }}
                >
                  <RefreshCw className="size-3" /> Use as draft
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 gap-1 text-[11px]"
                  onClick={() => {
                    copy(result);
                    toast.success("Copied");
                  }}
                >
                  <Copy className="size-3" /> Copy
                </Button>
              </div>
            )}
          </div>

          {warning && (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-[12px] text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0" /> {warning}
            </div>
          )}

          {loading ? (
            <div className="space-y-2 rounded-lg border border-border p-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className={`h-3.5 ${i === 5 ? "w-2/3" : "w-full"}`} />
              ))}
            </div>
          ) : result ? (
            <motion.textarea
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              value={result}
              onChange={(e) => setResult(e.target.value)}
              rows={16}
              className="min-h-[18rem] w-full flex-1 resize-y rounded-lg border border-border bg-card px-3 py-2.5 text-[13px] leading-relaxed outline-none focus:border-ring"
            />
          ) : (
            <div className="flex min-h-[18rem] flex-1 items-center justify-center rounded-lg border border-dashed border-border text-[13px] text-muted-foreground">
              Run a transform to see output
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ExportTab() {
  const { currentProjectId } = useUI();
  const { data: filesData } = useFiles({
    kind: "document",
    project_id: currentProjectId,
    limit: 50,
  });
  const papers = filesData?.items ?? [];
  const { data: notesData } = useNotes({ project_id: currentProjectId });
  const notes = notesData?.items ?? [];
  const { data: convos = [] } = useConversations();

  function download(url: string, fname: string) {
    const a = document.createElement("a");
    a.href = url;
    a.download = fname;
    a.click();
  }

  async function exportNotes(fmt: "md" | "txt" | "docx") {
    const res = await fetch("/api/export/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format: fmt, project_id: currentProjectId }),
    });
    if (!res.ok) {
      toast.error("Export failed");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    download(url, `notes.${fmt}`);
    URL.revokeObjectURL(url);
    toast.success(`Notes exported as .${fmt}`);
  }

  function ExportRow({
    title,
    subtitle,
    formats,
    onExport,
  }: {
    title: string;
    subtitle?: string;
    formats: { label: string; fmt: string }[];
    onExport: (fmt: string) => void;
  }) {
    return (
      <div className="flex items-center justify-between gap-3 border-b border-border py-2 last:border-0">
        <div className="min-w-0">
          <p className="truncate text-[13px] font-medium">{title}</p>
          {subtitle && (
            <p className="truncate text-[11px] text-muted-foreground">{subtitle}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {formats.map(({ label, fmt }) => (
            <Button
              key={fmt}
              size="sm"
              variant="outline"
              className="h-7 gap-1 px-2 text-[11px]"
              onClick={() => onExport(fmt)}
            >
              <Download className="size-3" /> {label}
            </Button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 border-b border-border pb-3 text-[12px]">
        <span className="text-muted-foreground">References</span>
        <Link to="/citations" className="inline-flex items-center gap-1 text-primary hover:underline">
          <Quote className="size-3.5" /> Open Citations
        </Link>
      </div>

      <section className="rounded-lg border border-border bg-card px-3">
        <div className="flex items-center gap-2 border-b border-border py-2">
          <StickyNote className="size-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold">Notes</h2>
          <span className="text-[11px] text-muted-foreground">({notes.length})</span>
        </div>
        <ExportRow
          title="All notes"
          subtitle={currentProjectId ? "Current project" : "All projects"}
          formats={[
            { label: ".md", fmt: "md" },
            { label: ".txt", fmt: "txt" },
            { label: ".docx", fmt: "docx" },
          ]}
          onExport={(fmt) => exportNotes(fmt as "md" | "txt" | "docx")}
        />
      </section>

      {papers.filter((p) => p.meta_status === "done").length > 0 && (
        <section className="rounded-lg border border-border bg-card px-3">
          <div className="flex items-center gap-2 border-b border-border py-2">
            <FileText className="size-3.5 text-muted-foreground" />
            <h2 className="text-[12px] font-semibold">Paper analyses</h2>
          </div>
          {papers
            .filter((p) => p.meta_status === "done")
            .map((p) => (
              <ExportRow
                key={p.id}
                title={p.title || p.name}
                subtitle={[p.authors?.split(";")[0]?.trim(), p.year]
                  .filter(Boolean)
                  .join(" · ")}
                formats={[
                  { label: ".md", fmt: "md" },
                  { label: ".txt", fmt: "txt" },
                ]}
                onExport={(fmt) =>
                  download(
                    writingApi.exportAnalysisUrl(p.id, fmt as "md" | "txt" | "docx"),
                    `analysis-${p.id}.${fmt}`,
                  )
                }
              />
            ))}
        </section>
      )}

      {convos.length > 0 && (
        <section className="rounded-lg border border-border bg-card px-3">
          <div className="flex items-center gap-2 border-b border-border py-2">
            <MessageSquare className="size-3.5 text-muted-foreground" />
            <h2 className="text-[12px] font-semibold">Conversations</h2>
          </div>
          {convos.slice(0, 10).map((c) => (
            <ExportRow
              key={c.id}
              title={c.title}
              formats={[
                { label: ".md", fmt: "md" },
                { label: ".txt", fmt: "txt" },
              ]}
              onExport={(fmt) =>
                download(
                  writingApi.exportChatUrl(c.id, fmt as "md" | "txt"),
                  `chat-${c.id}.${fmt}`,
                )
              }
            />
          ))}
        </section>
      )}

      <section className="rounded-lg border border-border bg-card px-3">
        <div className="flex items-center gap-2 border-b border-border py-2">
          <BookOpen className="size-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold">Citations</h2>
        </div>
        <ExportRow
          title="All citations"
          subtitle={currentProjectId ? "Current project" : "All projects"}
          formats={[
            { label: "APA", fmt: "apa" },
            { label: "IEEE", fmt: "ieee" },
            { label: "BibTeX", fmt: "bibtex" },
          ]}
          onExport={(fmt) => {
            const qs = currentProjectId
              ? `?format=${fmt}&project_id=${currentProjectId}`
              : `?format=${fmt}`;
            download(
              `/api/citations/export${qs}`,
              `references.${fmt === "bibtex" ? "bib" : "txt"}`,
            );
            toast.success(`Citations exported as ${fmt.toUpperCase()}`);
          }}
        />
      </section>
    </div>
  );
}

type Tab = "draft" | "export";

/** D7 T4 — Writing as grounded tool (draft + export), not pastel editor. */
export function WritingPage() {
  const [tab, setTab] = useState<Tab>("draft");

  return (
    <PageContainer title="Writing" dense>
      <div className="mb-4 flex items-center gap-1 border-b border-border">
        {(
          [
            { key: "draft" as const, label: "Draft" },
            { key: "export" as const, label: "Export" },
          ] as const
        ).map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={cn(
              "border-b-2 px-3 py-2 text-[13px] font-medium transition-colors",
              tab === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "draft" ? <DraftTab /> : <ExportTab />}
    </PageContainer>
  );
}
