import { useState } from "react";
import { motion } from "framer-motion";
import {
  Wand2, Loader2, Copy, Download, RefreshCw,
  BookOpen, GraduationCap, Minimize2, Maximize2,
  AlignLeft, FileText, MessageSquare, StickyNote, AlertTriangle,
} from "lucide-react";
import { PageContainer }  from "@/components/layout/PageContainer";
import { Button }         from "@/components/ui/button";
import { Skeleton }       from "@/components/ui/skeleton";
import { useFiles }       from "@/features/files/useFiles";
import { useNotes }       from "@/features/notes/useNotes";
import { useConversations } from "@/features/chat/hooks/useConversation";
import { useUI }          from "@/context/UIContext";
import { useClipboard }   from "@/hooks/useClipboard";
import { writingApi }     from "../api";
import { toast }          from "@/components/common/Toast";
import { cn }             from "@/lib/utils";
import type { WritingAction } from "@/types/api";

// ── Action config ─────────────────────────────────────────────────────────────
const ACTIONS: { key: WritingAction; label: string; icon: React.ReactNode; desc: string }[] = [
  {
    key: "rewrite_academic", label: "Rewrite academically",
    icon: <GraduationCap className="size-4" />,
    desc: "Formal academic register",
  },
  {
    key: "improve_grammar", label: "Fix grammar",
    icon: <AlignLeft className="size-4" />,
    desc: "Correct errors, preserve meaning",
  },
  {
    key: "improve_clarity", label: "Improve clarity",
    icon: <BookOpen className="size-4" />,
    desc: "Clearer, more readable prose",
  },
  {
    key: "expand", label: "Expand",
    icon: <Maximize2 className="size-4" />,
    desc: "Add explanation and detail",
  },
  {
    key: "shorten", label: "Shorten",
    icon: <Minimize2 className="size-4" />,
    desc: "Remove redundancy and filler",
  },
  {
    key: "generate_abstract", label: "Generate abstract",
    icon: <FileText className="size-4" />,
    desc: "150-250 word structured abstract",
  },
  {
    key: "improve_conclusion", label: "Strengthen conclusion",
    icon: <Wand2 className="size-4" />,
    desc: "Impactful, well-structured ending",
  },
];

// ── Writing Assistant tab ─────────────────────────────────────────────────────
function WritingAssistantTab() {
  const { copy } = useClipboard();
  const [input,   setInput]   = useState("");
  const [result,  setResult]  = useState("");
  const [warning, setWarning] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<WritingAction | null>(null);

  async function run(action: WritingAction) {
    if (!input.trim()) { toast.error("Paste some text first."); return; }
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
    } catch (e: any) {
      toast.error(e.message || "Writing assistant failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Input */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium">Your text</p>
          {input && (
            <span className="text-xs text-muted-foreground">{input.length} chars</span>
          )}
        </div>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Paste your text here — a paragraph, section, or abstract…"
          rows={12}
          className="w-full resize-y rounded-xl border border-border bg-card px-4 py-3 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/20 placeholder:text-muted-foreground/60"
        />

        {/* Action buttons */}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-2 xl:grid-cols-3">
          {ACTIONS.map(({ key, label, icon, desc }) => (
            <button
              key={key}
              onClick={() => run(key)}
              disabled={loading}
              title={desc}
              className={cn(
                "flex items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-xs font-medium transition-all",
                loading && activeAction === key
                  ? "border-primary bg-accent-soft text-primary"
                  : "border-border bg-card text-foreground hover:border-primary/40 hover:bg-muted/50",
                loading && activeAction !== key && "opacity-50 cursor-not-allowed",
              )}
            >
              {loading && activeAction === key
                ? <Loader2 className="size-3.5 shrink-0 animate-spin" />
                : <span className="shrink-0 text-muted-foreground">{icon}</span>}
              <span className="truncate">{label}</span>
            </button>
          ))}
        </div>

        <p className="text-[11px] text-muted-foreground">
          ⚠ Never fabricates citations, data, or experiments. If uncertain, it will say so.
        </p>
      </div>

      {/* Output */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium">Result</p>
          {result && (
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                className="h-7 gap-1.5 text-xs"
                onClick={() => { setInput(result); setResult(""); toast.success("Swapped to input"); }}
              >
                <RefreshCw className="size-3" /> Use as input
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="h-7 gap-1.5 text-xs"
                onClick={() => { copy(result); toast.success("Copied"); }}
              >
                <Copy className="size-3" /> Copy
              </Button>
            </div>
          )}
        </div>

        {warning && (
          <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-700 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
            <AlertTriangle className="size-3.5 shrink-0 mt-0.5" /> {warning}
          </div>
        )}

        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className={`h-4 ${i === 5 ? "w-2/3" : "w-full"}`} />
            ))}
          </div>
        ) : result ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.25 }}
          >
            <textarea
              value={result}
              onChange={(e) => setResult(e.target.value)}
              rows={12}
              className="w-full resize-y rounded-xl border border-primary/20 bg-accent-soft/40 px-4 py-3 text-sm outline-none"
            />
          </motion.div>
        ) : (
          <div className="flex h-[14rem] items-center justify-center rounded-xl border border-dashed border-border text-sm text-muted-foreground">
            Result will appear here
          </div>
        )}
      </div>
    </div>
  );
}

// ── Export Centre tab ─────────────────────────────────────────────────────────
function ExportCentreTab() {
  const { currentProjectId } = useUI();
  const { data: filesData }  = useFiles({ kind: "document", project_id: currentProjectId, limit: 50 });
  const papers               = filesData?.items ?? [];
  const { data: notesData }  = useNotes({ project_id: currentProjectId });
  const notes                = notesData?.items ?? [];
  const { data: convos = [] } = useConversations();

  function download(url: string, fname: string) {
    const a = document.createElement("a");
    a.href  = url;
    a.download = fname;
    a.click();
  }

  async function exportNotes(fmt: "md" | "txt" | "docx") {
    const res = await fetch("/api/export/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format: fmt, project_id: currentProjectId }),
    });
    if (!res.ok) { toast.error("Export failed"); return; }
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    download(url, `notes.${fmt}`);
    URL.revokeObjectURL(url);
    toast.success(`Notes exported as .${fmt}`);
  }

  function ExportRow({
    title, subtitle, formats, onExport,
  }: {
    title: string; subtitle?: string;
    formats: { label: string; fmt: string }[];
    onExport: (fmt: string) => void;
  }) {
    return (
      <div className="flex items-start justify-between gap-4 py-3 border-b border-border last:border-0">
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{title}</p>
          {subtitle && <p className="text-xs text-muted-foreground truncate">{subtitle}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {formats.map(({ label, fmt }) => (
            <Button
              key={fmt}
              size="sm"
              variant="outline"
              className="h-7 gap-1 text-xs"
              onClick={() => onExport(fmt)}
            >
              <Download className="size-3" /> {label}
            </Button>
          ))}
        </div>
      </div>
    );
  }

  const NOTE_FORMATS = [
    { label: ".md",   fmt: "md" },
    { label: ".txt",  fmt: "txt" },
    { label: ".docx", fmt: "docx" },
  ];
  const ANALYSIS_FORMATS = [
    { label: ".md",  fmt: "md" },
    { label: ".txt", fmt: "txt" },
  ];
  const CHAT_FORMATS = [
    { label: ".md",  fmt: "md" },
    { label: ".txt", fmt: "txt" },
  ];
  const CIT_FORMATS = [
    { label: "APA",     fmt: "apa" },
    { label: "IEEE",    fmt: "ieee" },
    { label: "BibTeX",  fmt: "bibtex" },
  ];

  return (
    <div className="space-y-8">
      {/* Notes */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <StickyNote className="size-4 text-amber-600 dark:text-amber-400" />
          <h2 className="text-sm font-semibold">Notes</h2>
          <span className="text-xs text-muted-foreground">({notes.length} notes)</span>
        </div>
        <div className="rounded-2xl border border-border bg-card px-4">
          <ExportRow
            title="All notes"
            subtitle={currentProjectId ? "Current project" : "All projects"}
            formats={NOTE_FORMATS}
            onExport={(fmt) => exportNotes(fmt as "md" | "txt" | "docx")}
          />
        </div>
      </section>

      {/* Paper analyses */}
      {papers.length > 0 && (
        <section>
          <div className="mb-3 flex items-center gap-2">
            <FileText className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Paper Analyses</h2>
          </div>
          <div className="rounded-2xl border border-border bg-card px-4">
            {papers.filter(p => p.meta_status === "done").map((p) => (
              <ExportRow
                key={p.id}
                title={p.title || p.name}
                subtitle={[p.authors?.split(";")[0]?.trim(), p.year].filter(Boolean).join(" · ")}
                formats={ANALYSIS_FORMATS}
                onExport={(fmt) => download(
                  writingApi.exportAnalysisUrl(p.id, fmt as "md" | "txt" | "docx"),
                  `analysis-${p.id}.${fmt}`,
                )}
              />
            ))}
            {papers.filter(p => p.meta_status !== "done").length > 0 && (
              <p className="py-2 text-xs text-muted-foreground">
                {papers.filter(p => p.meta_status !== "done").length} paper{papers.filter(p => p.meta_status !== "done").length > 1 ? "s" : ""} still being analysed
              </p>
            )}
          </div>
        </section>
      )}

      {/* Chats */}
      {convos.length > 0 && (
        <section>
          <div className="mb-3 flex items-center gap-2">
            <MessageSquare className="size-4 text-blue-600 dark:text-blue-400" />
            <h2 className="text-sm font-semibold">Conversations</h2>
          </div>
          <div className="rounded-2xl border border-border bg-card px-4">
            {convos.slice(0, 10).map((c) => (
              <ExportRow
                key={c.id}
                title={c.title}
                formats={CHAT_FORMATS}
                onExport={(fmt) => download(
                  writingApi.exportChatUrl(c.id, fmt as "md" | "txt"),
                  `chat-${c.id}.${fmt}`,
                )}
              />
            ))}
          </div>
        </section>
      )}

      {/* Citations */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <BookOpen className="size-4 text-emerald-600 dark:text-emerald-400" />
          <h2 className="text-sm font-semibold">Citations</h2>
        </div>
        <div className="rounded-2xl border border-border bg-card px-4">
          <ExportRow
            title="All citations"
            subtitle={currentProjectId ? "Current project" : "All projects"}
            formats={CIT_FORMATS}
            onExport={(fmt) => {
              const qs = currentProjectId ? `?format=${fmt}&project_id=${currentProjectId}` : `?format=${fmt}`;
              download(`/api/citations/export${qs}`, `references.${fmt === "bibtex" ? "bib" : "txt"}`);
              toast.success(`Citations exported as ${fmt.toUpperCase()}`);
            }}
          />
        </div>
      </section>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
type Tab = "writing" | "export";

export function WritingPage() {
  const [tab, setTab] = useState<Tab>("writing");

  const TABS: { key: Tab; label: string }[] = [
    { key: "writing", label: "AI Writing Assistant" },
    { key: "export",  label: "Export Centre" },
  ];

  return (
    <PageContainer
      title="Writing & Export"
      description="Transform your text with AI and export your research in any format."
    >
      {/* Tab bar */}
      <div className="flex items-center gap-1 rounded-xl border border-border bg-muted/40 p-1 mb-6 w-fit">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={cn(
              "rounded-lg px-5 py-2 text-sm font-medium transition-all",
              tab === key ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "writing" ? <WritingAssistantTab /> : <ExportCentreTab />}
    </PageContainer>
  );
}
