import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Wand2, Loader2, Copy, Download, RefreshCw,
  BookOpen, GraduationCap, Minimize2, Maximize2,
  AlignLeft, FileText, MessageSquare, StickyNote, AlertTriangle,
  Quote, Plus, History,
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
import { trackWritingEvent } from "../utils/telemetry";

const ACTIONS: { key: WritingAction; label: string; icon: React.ReactNode; desc: string }[] = [
  { key: "rewrite_academic", label: "Academic", icon: <GraduationCap className="size-3.5" />, desc: "Formal academic register" },
  { key: "improve_grammar", label: "Grammar", icon: <AlignLeft className="size-3.5" />, desc: "Correct errors" },
  { key: "improve_clarity", label: "Clarity", icon: <BookOpen className="size-3.5" />, desc: "Clearer prose" },
  { key: "expand", label: "Expand", icon: <Maximize2 className="size-3.5" />, desc: "Add detail" },
  { key: "shorten", label: "Shorten", icon: <Minimize2 className="size-3.5" />, desc: "Cut filler" },
  { key: "generate_abstract", label: "Abstract", icon: <FileText className="size-3.5" />, desc: "Structured abstract" },
  { key: "improve_conclusion", label: "Conclusion", icon: <Wand2 className="size-3.5" />, desc: "Strengthen ending" },
];

function buildAutosaveKey(
  docId: number,
  version: number,
  title: string,
  content: string,
) {
  const preview = `${title}|${content}`.slice(0, 64);
  let hash = 0;
  for (let i = 0; i < preview.length; i += 1) {
    hash = (hash * 31 + preview.charCodeAt(i)) >>> 0;
  }
  return `doc-${docId}-v${version}-${hash}`;
}

function DraftTab() {
  const { currentProjectId } = useUI();
  const qc = useQueryClient();
  const { copy } = useClipboard();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [input, setInput] = useState("");
  const [result, setResult] = useState("");
  const [warning, setWarning] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<WritingAction | null>(null);
  const [saveState, setSaveState] = useState<
    "idle" | "dirty" | "scheduled" | "saving" | "saved" | "conflict" | "error"
  >("idle");
  const [version, setVersion] = useState<number>(1);
  const [lifecycleView, setLifecycleView] = useState<"active" | "archived" | "deleted">("active");
  const retryTimeoutRef = useRef<number | null>(null);
  const [isOffline, setIsOffline] = useState<boolean>(!window.navigator.onLine);

  const docsQuery = useQuery({
    queryKey: ["writing", "documents", currentProjectId ?? "all", lifecycleView],
    queryFn: () =>
      writingApi.listDocuments(currentProjectId as number, {
        status: lifecycleView,
        includeArchived: lifecycleView !== "active",
        includeDeleted: lifecycleView === "deleted",
      }),
    enabled: currentProjectId != null,
  });
  const docs = docsQuery.data?.items;

  const activeDoc = (docs ?? []).find((d) => d.id === activeId) ?? null;

  useEffect(() => {
    if (!docs?.length) {
      setActiveId(null);
      setDraftTitle("");
      setInput("");
      setVersion(1);
      return;
    }
    if (activeId && docs.some((d) => d.id === activeId)) return;
    const d = docs[0];
    setActiveId(d.id);
    setDraftTitle(d.title || "Untitled draft");
    setInput(d.content || "");
    setVersion(d.current_version || 1);
    setSaveState("saved");
  }, [activeId, docs]);

  const createDoc = useMutation({
    mutationFn: () =>
      writingApi.createDocument({
        title: "Untitled draft",
        content: "",
        project_id: currentProjectId as number,
        editor_kind: "markdown",
      }),
    onSuccess: (doc) => {
      qc.invalidateQueries({ queryKey: ["writing", "documents", currentProjectId ?? "all"] });
      setActiveId(doc.id);
      setDraftTitle(doc.title || "Untitled draft");
      setInput(doc.content || "");
      setVersion(doc.current_version || 1);
      setSaveState("saved");
      toast.success("Draft created");
    },
    onError: () => toast.error("Could not create draft"),
  });

  const updateStatus = useMutation({
    mutationFn: (payload: { id: number; status: "active" | "archived" | "deleted" }) =>
      writingApi.updateDocument(payload.id, {
        status: payload.status,
        current_version: version,
      }),
    onSuccess: (doc) => {
      qc.invalidateQueries({ queryKey: ["writing", "documents", currentProjectId ?? "all"] });
      setVersion(doc.current_version || version);
      toast.success(`Moved to ${doc.status}`);
    },
    onError: () => toast.error("Could not update document status"),
  });

  const autosave = useMutation({
    mutationFn: (payload: {
      id: number;
      title: string;
      content: string;
      currentVersion: number;
      idempotencyKey: string;
    }) =>
      writingApi.autosaveDocument(payload.id, {
        title: payload.title,
        content: payload.content,
        current_version: payload.currentVersion,
        idempotency_key: payload.idempotencyKey,
      }),
    onSuccess: (res) => {
      setSaveState("saved");
      setVersion(res.document.current_version);
      trackWritingEvent("autosave_succeeded", {
        documentId: res.document.id,
        version: res.document.current_version,
        replay: res.idempotent_replay,
      });
      qc.invalidateQueries({ queryKey: ["writing", "documents", currentProjectId ?? "all"] });
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : "Autosave failed";
      if (message.includes("version_conflict") || message.includes("409")) {
        setSaveState("conflict");
        trackWritingEvent("autosave_conflict");
        toast.error("Version conflict. Refresh and retry.");
      } else {
        setSaveState("error");
        trackWritingEvent("autosave_failed");
        toast.error("Autosave failed. Retrying shortly.");
        if (retryTimeoutRef.current) window.clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = window.setTimeout(() => {
          if (!activeDoc) return;
          setSaveState("scheduled");
          autosave.mutate({
            id: activeDoc.id,
            title: draftTitle,
            content: input,
            currentVersion: version,
            idempotencyKey: buildAutosaveKey(activeDoc.id, version, draftTitle, input),
          });
        }, 1500);
      }
    },
  });

  useEffect(() => {
    const handleOffline = () => {
      setIsOffline(true);
      trackWritingEvent("writing_offline");
    };
    const handleOnline = () => {
      setIsOffline(false);
      trackWritingEvent("writing_online");
      if (saveState === "error" || saveState === "dirty") {
        setSaveState("scheduled");
      }
    };
    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);
    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, [saveState]);

  useEffect(() => {
    if (currentProjectId == null) return;
    if (!activeDoc) return;
    if (isOffline || saveState === "conflict") return;
    if (draftTitle === (activeDoc.title || "") && input === (activeDoc.content || "")) return;
    setSaveState("scheduled");
    const handle = window.setTimeout(() => {
      setSaveState("saving");
      trackWritingEvent("autosave_attempted", { documentId: activeDoc.id, version });
      autosave.mutate({
        id: activeDoc.id,
        title: draftTitle,
        content: input,
        currentVersion: version,
        idempotencyKey: buildAutosaveKey(activeDoc.id, version, draftTitle, input),
      });
    }, 1200);
    return () => window.clearTimeout(handle);
  }, [activeDoc, autosave, currentProjectId, draftTitle, input, isOffline, saveState, version]);

  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) window.clearTimeout(retryTimeoutRef.current);
    };
  }, []);

  useEffect(() => {
    if (!activeDoc) return;
    if (saveState === "saving" || saveState === "scheduled" || saveState === "conflict") return;
    const changed = draftTitle !== (activeDoc.title || "") || input !== (activeDoc.content || "");
    setSaveState(changed ? "dirty" : "saved");
  }, [activeDoc, draftTitle, input, saveState]);

  const versionsQuery = useQuery({
    queryKey: ["writing", "versions", activeId ?? "none"],
    queryFn: () => writingApi.listVersions(activeId as number),
    enabled: !!activeId,
  });

  const restoreVersion = useMutation({
    mutationFn: (versionId: number) => writingApi.restoreVersion(activeId as number, versionId),
    onSuccess: (doc) => {
      setDraftTitle(doc.title || "Untitled draft");
      setInput(doc.content || "");
      setVersion(doc.current_version || 1);
      setSaveState("saved");
      qc.invalidateQueries({ queryKey: ["writing", "documents", currentProjectId ?? "all"] });
      qc.invalidateQueries({ queryKey: ["writing", "versions", activeId ?? "none"] });
      toast.success(
        doc.restored_from_version_id
          ? `Restored from version #${doc.restored_from_version_id}`
          : "Version restored",
      );
    },
    onError: () => toast.error("Could not restore version"),
  });

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
      {currentProjectId == null && (
        <div className="rounded-md border border-border bg-card p-3 text-[12px] text-muted-foreground">
          Select a project to start writing. Documents are always project-scoped.
        </div>
      )}
      {isOffline && (
        <div
          role="status"
          aria-live="polite"
          className="rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-[12px] text-blue-900 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200"
        >
          You are offline. Changes stay local until the connection returns.
        </div>
      )}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 rounded border border-border p-1">
          {(
            [
              { key: "active" as const, label: "Active" },
              { key: "archived" as const, label: "Archived" },
              { key: "deleted" as const, label: "Deleted" },
            ] as const
          ).map((it) => (
            <button
              key={it.key}
              type="button"
              onClick={() => setLifecycleView(it.key)}
              className={cn(
                "rounded px-2 py-1 text-[11px]",
                lifecycleView === it.key
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted/50",
              )}
            >
              {it.label}
            </button>
          ))}
        </div>
        <select
          aria-label="Select writing document"
          className="h-8 min-w-[220px] rounded-md border border-border bg-card px-2 text-[12px]"
          value={activeId ?? ""}
          onChange={(e) => {
            const nextId = Number(e.target.value || 0);
            const doc = (docs ?? []).find((x) => x.id === nextId);
            if (!doc) return;
            setActiveId(doc.id);
            setDraftTitle(doc.title || "Untitled draft");
            setInput(doc.content || "");
            setVersion(doc.current_version || 1);
          }}
        >
          {(docs ?? []).map((d) => (
            <option key={d.id} value={d.id}>
              {d.title || "Untitled draft"}
            </option>
          ))}
        </select>
        <Button
          size="sm"
          variant="outline"
          className="h-8 gap-1 text-[11px]"
          onClick={() => createDoc.mutate()}
          disabled={createDoc.isPending || currentProjectId == null}
        >
          <Plus className="size-3.5" /> New draft
        </Button>
        <span className="ml-auto text-[11px] text-muted-foreground" role="status" aria-live="polite">
          {saveState === "scheduled"
            ? "Save scheduled"
            : saveState === "saving"
              ? "Saving..."
              : saveState === "conflict"
                ? "Conflict detected"
                : saveState === "error"
                  ? "Save failed"
                  : saveState === "dirty"
                    ? "Unsaved changes"
                    : "Saved"}
        </span>
      </div>
      {saveState === "conflict" && (
        <div
          role="alert"
          className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-[12px] text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
        >
          Another version was saved elsewhere. Refresh this document before continuing.
        </div>
      )}
      {activeDoc && (
        <div className="flex items-center gap-2 text-[11px]">
          {activeDoc.status === "active" && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-[11px]"
              onClick={() => updateStatus.mutate({ id: activeDoc.id, status: "archived" })}
            >
              Archive
            </Button>
          )}
          {activeDoc.status === "archived" && (
            <>
              <Button
                size="sm"
                variant="outline"
                className="h-7 px-2 text-[11px]"
                onClick={() => updateStatus.mutate({ id: activeDoc.id, status: "active" })}
              >
                Restore Active
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-7 px-2 text-[11px]"
                onClick={() => updateStatus.mutate({ id: activeDoc.id, status: "deleted" })}
              >
                Move to Deleted
              </Button>
            </>
          )}
          {activeDoc.status === "deleted" && (
            <span className="text-muted-foreground">Deleted documents are read-only in Week 1.</span>
          )}
        </div>
      )}

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

      <div className="grid min-h-0 gap-3 lg:grid-cols-[1fr_1fr_260px]">
        <div className="flex min-h-0 flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <input
              value={draftTitle}
              onChange={(e) => setDraftTitle(e.target.value)}
              className="h-7 w-full rounded border border-border bg-card px-2 text-[12px] font-medium text-foreground"
              placeholder="Untitled draft"
            />
            {input && (
              <span className="text-[11px] tabular-nums text-muted-foreground">{input.length}</span>
            )}
          </div>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Paste a paragraph, section, or abstract…"
            rows={16}
            aria-label="Writing draft editor"
            disabled={activeDoc?.status === "deleted"}
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

        <div className="rounded-lg border border-border bg-card">
          <div className="flex items-center gap-2 border-b border-border px-3 py-2 text-[12px] font-medium">
            <History className="size-3.5 text-muted-foreground" />
            Version history
          </div>
          <div className="max-h-[24rem] overflow-auto p-2">
            {(versionsQuery.data?.items ?? []).map((v) => (
              <button
                key={v.id}
                type="button"
                onClick={() => restoreVersion.mutate(v.id)}
                className="mb-1 flex w-full items-center justify-between rounded border border-border px-2 py-1 text-left text-[11px] hover:bg-muted/40"
              >
                <span>v{v.version_no} · {v.source}</span>
                <span className="text-muted-foreground">
                  {v.created_at ? new Date(v.created_at).toLocaleTimeString() : ""}
                </span>
              </button>
            ))}
            {!versionsQuery.data?.items?.length && (
              <p className="px-1 py-2 text-[11px] text-muted-foreground">No versions yet.</p>
            )}
          </div>
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
