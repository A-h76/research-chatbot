import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Wand2, Loader2, Copy, Download, RefreshCw,
  BookOpen, GraduationCap, Minimize2, Maximize2,
  AlignLeft, FileText, MessageSquare, StickyNote, AlertTriangle,
  Quote, Plus,
} from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { WritingDeskSkeleton } from "@/components/common/ResearchSkeletons";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
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
import {
  classifyAutosaveFailure,
  shouldResumeAutosaveOnOnline,
  shouldScheduleAutosave,
  type WritingSaveState,
} from "../utils/autosavePolicy";
import { mapWritingError } from "../utils/errorMap";
import { trackWorkflowEvent } from "@/lib/workflowTelemetry";
import { loadResearchPrefs } from "@/features/settings/lib/researchPrefs";
import { EvidenceInspectorPanel } from "@/features/evidence/components/EvidenceInspectorPanel";
import { useEvidenceExplain } from "@/features/evidence/hooks/useEvidenceExplain";
import { useGroundedWriting, type WritingSectionType, type GroundedWritingSection } from "@/features/evidence/hooks/useGroundedWriting";
import { evidenceApi } from "@/features/evidence/api";
import {
  GroundedDraftVerify,
  persistGroundedBindings,
} from "@/features/writing/components/GroundedDraftVerify";
import { CitationInsertPicker } from "@/features/writing/components/CitationInsertPicker";
import {
  insertAtCaret,
  removeEvidenceMarker,
  selectedEvidenceMarkerId,
} from "@/features/writing/utils/citeDraftHelpers";
import { ResearchProgressStage } from "@/features/writing/components/ResearchProgressStage";
import { WritingOutlineRail } from "@/features/writing/components/WritingOutlineRail";
import {
  downloadMarkdownFile,
  downloadTextFile,
  loadGroundedExportSnapshot,
  saveGroundedExportSnapshot,
  canExportGroundedLitReview,
} from "@/features/writing/utils/groundedMarkdownExport";

const ACTIONS: { key: WritingAction; label: string; icon: React.ReactNode; desc: string }[] = [
  { key: "rewrite_academic", label: "Academic", icon: <GraduationCap className="size-3.5" />, desc: "Formal academic register" },
  { key: "improve_grammar", label: "Grammar", icon: <AlignLeft className="size-3.5" />, desc: "Correct errors" },
  { key: "improve_clarity", label: "Clarity", icon: <BookOpen className="size-3.5" />, desc: "Clearer prose" },
  { key: "expand", label: "Expand", icon: <Maximize2 className="size-3.5" />, desc: "Add detail" },
  { key: "shorten", label: "Shorten", icon: <Minimize2 className="size-3.5" />, desc: "Cut filler" },
  { key: "generate_abstract", label: "Abstract", icon: <FileText className="size-3.5" />, desc: "Structured abstract" },
  { key: "improve_conclusion", label: "Conclusion", icon: <Wand2 className="size-3.5" />, desc: "Strengthen ending" },
];

function FlaskConicalIcon() {
  // Local inline icon to avoid depending on lucide version for FlaskConical
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-3.5"
      aria-hidden
    >
      <path d="M10 2v7.527a2 2 0 0 1-.211.896L4.72 20.55a1 1 0 0 0 .9 1.45h12.76a1 1 0 0 0 .9-1.45l-5.069-10.127A2 2 0 0 1 14 9.527V2" />
      <path d="M8.5 2h7" />
      <path d="M7 16h10" />
    </svg>
  );
}

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
  const [saveState, setSaveState] = useState<WritingSaveState>("idle");
  const [version, setVersion] = useState<number>(1);
  const [lifecycleView, setLifecycleView] = useState<"active" | "archived" | "deleted">("active");
  const retryTimeoutRef = useRef<number | null>(null);
  const [isOffline, setIsOffline] = useState<boolean>(!window.navigator.onLine);
  const [selectedText, setSelectedText] = useState("");
  const [evidenceRefresh, setEvidenceRefresh] = useState(0);
  const [reviewerRefresh, setReviewerRefresh] = useState(0);
  const [citePickerOpen, setCitePickerOpen] = useState(false);
  const [citeHoverPreview, setCiteHoverPreview] = useState<string | null>(null);
  const [sectionType, setSectionType] = useState<WritingSectionType>("literature_review");
  const [groundedBaseline, setGroundedBaseline] = useState<string | null>(null);
  const [editsSinceInsert, setEditsSinceInsert] = useState(0);
  const [confirmDeleteDoc, setConfirmDeleteDoc] = useState(false);
  const editorRef = useRef<HTMLTextAreaElement | null>(null);
  const litReviewBtnRef = useRef<HTMLButtonElement | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const handledActionRef = useRef<string | null>(null);

  const evidenceExplain = useEvidenceExplain({
    documentId: activeId,
    projectId: currentProjectId,
    selectedText,
    enabled: activeId != null && currentProjectId != null,
    refreshKey: evidenceRefresh,
  });
  const grounded = useGroundedWriting();

  useEffect(() => {
    if (!grounded.last || grounded.last.status !== "ok" || activeId == null) return;
    saveGroundedExportSnapshot({
      documentId: activeId,
      title: draftTitle || "Literature review",
      body: grounded.last.paragraph || input,
      writing: grounded.last,
      writing_version: grounded.last.writing_version,
      savedAt: new Date().toISOString(),
    });
    setReviewerRefresh((n) => n + 1);
    // Only when a new grounded result arrives — not on every manuscript keystroke.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional: grounded.last identity
  }, [grounded.last, activeId]);

  const docsQuery = useQuery({
    queryKey: ["writing", "documents", currentProjectId ?? "all", lifecycleView],
    queryFn: () =>
      writingApi.listDocuments(currentProjectId as number, {
        // "Active" means the working set (draft + active). New docs start as draft.
        status: lifecycleView === "active" ? undefined : lifecycleView,
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
    const docParam = Number(searchParams.get("doc"));
    const fromQuery =
      Number.isFinite(docParam) && docParam > 0
        ? docs.find((d) => d.id === docParam)
        : undefined;
    const d = fromQuery ?? docs[0];
    setActiveId(d.id);
    setDraftTitle(d.title || "Untitled draft");
    setInput(d.content || "");
    setVersion(d.current_version || 1);
    setSaveState("saved");
  }, [activeId, docs, searchParams]);

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
      const kind = classifyAutosaveFailure(message);
      if (kind === "conflict") {
        setSaveState("conflict");
        trackWritingEvent("autosave_conflict");
        toast.error(mapWritingError(err));
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
      if (shouldResumeAutosaveOnOnline(saveState)) {
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
    if (!shouldScheduleAutosave({ isOffline, saveState })) return;
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

  function runGroundedGenerate() {
    if (activeId == null || currentProjectId == null) {
      toast.error("Select a project document first");
      return;
    }
    const focus = selectedText.trim() || input.trim();
    if (!focus) {
      toast.error("Add manuscript text or select a sentence first");
      return;
    }
    grounded.generate({
      projectId: currentProjectId,
      documentId: activeId,
      selectedText,
      draftFallback: input,
      sectionType,
    });
  }

  /** Phase A.1: Accept must merge into manuscript, persist bindings, and save immediately. */
  async function acceptGroundedIntoManuscript(opts?: {
    paragraph?: string;
    sectionIds?: string[];
  }) {
    if (!grounded.last || activeId == null || activeDoc == null) return;
    if (grounded.last.status === "blocked" || grounded.last.accept_allowed === false) {
      toast.error(
        grounded.last.blocked_reason === "reviewer_failed"
          ? "Accept blocked — fix Research Reviewer errors first"
          : "Accept blocked — insufficient or ungrounded evidence",
      );
      return;
    }
    if (grounded.last.review?.status === "fail") {
      const blocking = (grounded.last.review.issues || []).some(
        (i) =>
          i.severity === "error" &&
          ["unbound_paragraph", "unsupported_claim", "orphan_citation", "empty_section"].includes(
            i.code,
          ),
      );
      if (blocking) {
        toast.error("Accept blocked — Research Reviewer found grounding errors");
        return;
      }
    }
    const nextPara = (opts?.paragraph || grounded.last.paragraph || "").trim();
    if (!nextPara) {
      toast.error("Nothing to accept into the manuscript");
      return;
    }
    const merged = input.trim() ? `${input.trim()}\n\n${nextPara}` : nextPara;
    setInput(merged);
    setGroundedBaseline(merged);
    setEditsSinceInsert(0);

    const persist = await persistGroundedBindings({
      documentId: activeId,
      writing: grounded.last,
      sectionIds: opts?.sectionIds,
      createBinding: evidenceApi.createBinding,
    });
    saveGroundedExportSnapshot({
      documentId: activeId,
      title: draftTitle || "Literature review",
      body: merged,
      writing: grounded.last,
      writing_version: grounded.last.writing_version,
      savedAt: new Date().toISOString(),
    });
    trackWritingEvent("grounded_insert", {
      section_type: grounded.last.section_type || "literature_review",
      grounding_pct: grounded.last.metrics?.grounding_pct,
      reviewer_pass_rate: grounded.last.metrics?.reviewer_pass_rate,
      citation_count: grounded.last.citations.length,
      bindings_saved: persist.saved,
      bindings_failed: persist.failed,
      section_ids: opts?.sectionIds?.join(",") || "all",
    });

    setSaveState("saving");
    trackWritingEvent("autosave_attempted", { documentId: activeId, version });
    autosave.mutate({
      id: activeId,
      title: draftTitle.trim() || "Untitled draft",
      content: merged,
      currentVersion: version,
      idempotencyKey: buildAutosaveKey(activeId, version, draftTitle, merged),
    });

    if (persist.failed > 0) {
      toast.error(`Accepted draft; ${persist.failed} evidence link(s) failed to save`);
    } else {
      toast.success(
        persist.saved > 0
          ? `Accepted · ${persist.saved} evidence link(s) saved`
          : "Accepted into manuscript — verify links before export",
      );
    }
  }

  async function acceptGroundedSection(section: GroundedWritingSection) {
    const para = (section.paragraph || "").trim();
    if (!para) return;
    await acceptGroundedIntoManuscript({
      paragraph: para,
      sectionIds: [section.id],
    });
  }

  function scheduleCiteAutosave(nextContent: string) {
    if (activeId == null || activeDoc == null || activeDoc.status === "deleted") return;
    setSaveState("saving");
    autosave.mutate({
      id: activeId,
      title: draftTitle.trim() || "Untitled draft",
      content: nextContent,
      currentVersion: version,
      idempotencyKey: buildAutosaveKey(activeId, version, draftTitle, nextContent),
    });
  }

  async function handleCiteInsert(payload: {
    insertText: string;
    evidenceId: number | null;
    citationId: number | null;
    grounded: boolean;
    preview?: string;
  }) {
    if (activeId == null) {
      toast.error("Open a draft first");
      return;
    }
    const el = editorRef.current;
    const start = el?.selectionStart ?? input.length;
    const end = el?.selectionEnd ?? start;
    const { content: next, caret } = insertAtCaret(input, payload.insertText, start, end);
    setInput(next);
    scheduleCiteAutosave(next);
    requestAnimationFrame(() => {
      const ta = editorRef.current;
      if (!ta) return;
      ta.focus();
      ta.setSelectionRange(caret, caret);
    });

    if (payload.evidenceId != null) {
      try {
        await evidenceApi.createBinding(activeId, {
          evidence_object_id: payload.evidenceId,
          block_id: "cite_insert",
          selected_text: payload.insertText,
          relation: "supports",
        });
      } catch {
        toast.error("Citation inserted, but evidence binding failed to save");
        return;
      }
    }

    if (payload.grounded) {
      toast.success(`Inserted grounded cite ${payload.insertText}`);
    } else {
      toast.success(
        "Inserted library cite (no matching EvidenceObject — Reviewer won't validate it)",
      );
    }
    if (payload.preview) setCiteHoverPreview(payload.preview);
  }

  async function removeSelectedCite() {
    if (activeId == null) return;
    const el = editorRef.current;
    if (!el) return;
    const eid = selectedEvidenceMarkerId(input, el.selectionStart, el.selectionEnd);
    if (eid == null) {
      toast.error("Select a [#id] citation marker to remove");
      return;
    }
    const { content: next, removed } = removeEvidenceMarker(input, eid);
    if (!removed) return;
    setInput(next);
    scheduleCiteAutosave(next);
    try {
      const listed = await evidenceApi.listBindings(activeId);
      const targets = listed.items.filter((b) => b.evidence_object_id === eid);
      await Promise.all(targets.map((b) => evidenceApi.deleteBinding(b.id)));
    } catch {
      toast.error("Removed from draft; binding cleanup failed");
      return;
    }
    toast.success(`Removed [#${eid}]`);
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!(e.ctrlKey || e.metaKey) || !e.shiftKey) return;
      if (e.key.toLowerCase() !== "c") return;
      if (activeId == null || currentProjectId == null) return;
      const t = e.target as HTMLElement | null;
      if (t && t.tagName !== "TEXTAREA" && t.tagName !== "INPUT" && !t.isContentEditable) {
        // allow from page when writing desk focused
      }
      e.preventDefault();
      setCitePickerOpen(true);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeId, currentProjectId]);

  /** ⌘K deep-links: ?action=lit-review · ?focus=evidence */
  useEffect(() => {
    const action = searchParams.get("action");
    const focusTarget = searchParams.get("focus");

    if (focusTarget === "evidence") {
      const next = new URLSearchParams(searchParams);
      next.delete("focus");
      setSearchParams(next, { replace: true });
      window.requestAnimationFrame(() => {
        document.getElementById("writing-evidence-rail")?.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      });
    }

    if (action !== "lit-review") {
      handledActionRef.current = null;
      return;
    }
    if (docsQuery.isLoading || docsQuery.isFetching) return;
    if (activeId == null || currentProjectId == null) return;
    if (activeDoc?.status === "deleted") return;
    if (handledActionRef.current === "lit-review") return;
    handledActionRef.current = "lit-review";

    const next = new URLSearchParams(searchParams);
    next.delete("action");
    setSearchParams(next, { replace: true });

    const seed = selectedText.trim() || input.trim();
    if (seed) {
      grounded.generate({
        projectId: currentProjectId,
        documentId: activeId,
        selectedText,
        draftFallback: input,
        sectionType,
      });
    } else {
      litReviewBtnRef.current?.focus();
      toast.error("Add manuscript notes or a research question, then write the literature review");
    }
    // Intentionally keyed on URL + doc readiness, not every keystroke
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    searchParams,
    activeId,
    currentProjectId,
    activeDoc?.status,
    docsQuery.isLoading,
    docsQuery.isFetching,
  ]);

  return (
    <div className="space-y-3">
      {currentProjectId == null && (
        <div className="rounded-md border border-border bg-card p-3 text-[12px] text-muted-foreground">
          Select a project to open the writing desk. Documents are always project-scoped.
        </div>
      )}
      {currentProjectId != null && docsQuery.isLoading ? (
        <WritingDeskSkeleton />
      ) : (
        <>
      {isOffline && (
        <div
          role="status"
          aria-live="polite"
          className="rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-[12px] text-blue-900 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200"
        >
          You are offline. Changes stay local until the connection returns.
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
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
          className="h-8 min-w-[180px] rounded-md border border-border bg-card px-2 text-[12px]"
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
        {activeDoc?.status === "active" && (
          <Button
            size="sm"
            variant="ghost"
            className="h-8 px-2 text-[11px]"
            onClick={() => updateStatus.mutate({ id: activeDoc.id, status: "archived" })}
          >
            Archive
          </Button>
        )}
        {activeDoc?.status === "archived" && (
          <>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 px-2 text-[11px]"
              onClick={() => updateStatus.mutate({ id: activeDoc.id, status: "active" })}
            >
              Restore
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 px-2 text-[11px]"
              onClick={() => setConfirmDeleteDoc(true)}
            >
              Delete
            </Button>
          </>
        )}
        {activeDoc?.status === "deleted" && (
          <span className="text-[11px] text-muted-foreground">Deleted drafts are read-only.</span>
        )}
        <span className="ml-auto text-[11px] text-muted-foreground" role="status" aria-live="polite">
          {saveState === "scheduled"
            ? "Save scheduled"
            : saveState === "saving"
              ? "Saving…"
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
          className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-[12px] text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
        >
          <span>
            Another version was saved elsewhere. Reload the latest from the server
            before continuing (local unsaved text will be replaced).
          </span>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-7 shrink-0 border-amber-400/60 bg-transparent text-[11px]"
            onClick={async () => {
              if (activeId == null || currentProjectId == null) return;
              try {
                const res = await writingApi.listDocuments(currentProjectId, {
                  status: lifecycleView === "active" ? undefined : lifecycleView,
                  includeArchived: lifecycleView !== "active",
                  includeDeleted: lifecycleView === "deleted",
                });
                qc.setQueryData(
                  ["writing", "documents", currentProjectId, lifecycleView],
                  res,
                );
                await qc.invalidateQueries({
                  queryKey: ["writing", "versions", activeId],
                });
                const latest = res.items.find((d) => d.id === activeId);
                if (latest) {
                  setDraftTitle(latest.title || "Untitled draft");
                  setInput(latest.content || "");
                  setVersion(latest.current_version || 1);
                }
                setSaveState("saved");
                toast.success("Reloaded latest from server");
              } catch {
                toast.error("Could not reload document");
              }
            }}
          >
            <RefreshCw className="size-3" /> Reload latest
          </Button>
        </div>
      )}

      <ResearchConfidenceStrip
        metrics={grounded.last?.metrics}
        review={grounded.last?.review}
        reviewerVersion={grounded.last?.review?.reviewer_version}
      />

      <div className="flex flex-wrap items-center gap-2">
        <button
          ref={litReviewBtnRef}
          type="button"
          id="write-literature-review"
          disabled={
            grounded.isPending ||
            activeId == null ||
            currentProjectId == null ||
            activeDoc?.status === "deleted"
          }
          title="Write this outline section from accepted EvidenceObjects"
          className={cn(
            "inline-flex h-9 items-center gap-1.5 rounded-md px-3 text-[13px] font-medium transition-colors",
            grounded.isPending
              ? "bg-primary/90 text-primary-foreground"
              : "bg-primary text-primary-foreground hover:opacity-90",
            "disabled:opacity-50",
          )}
          onClick={runGroundedGenerate}
        >
          {grounded.isPending ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <FlaskConicalIcon />
          )}
          Write {sectionType === "literature_review" ? "literature review" : sectionType.replaceAll("_", " ")}
        </button>
        <span className="text-[12px] text-muted-foreground">
          Outline → Evidence → Verify → Accept · click [#id] markers to inspect
        </span>
      </div>

      <details className="rounded-md border border-border bg-card/50 px-3 py-2">
        <summary className="cursor-pointer text-[12px] font-medium text-muted-foreground">
          Style transforms (not evidence-backed)
        </summary>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Style-only edits do not cite EvidenceObjects. Use Write grounded draft for research-backed
          prose.
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-1.5 pb-1">
          {ACTIONS.map(({ key, label, icon, desc }) => (
            <button
              key={key}
              type="button"
              onClick={() => run(key)}
              disabled={loading}
              title={`${desc} (not evidence-backed)`}
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
        </div>
      </details>

      {/* Writing desk: Outline | Manuscript | Evidence */}
      <div className="grid min-h-[28rem] gap-3 lg:grid-cols-[220px_minmax(0,1fr)_300px]">
        <WritingOutlineRail
          sectionType={sectionType}
          onSectionTypeChange={setSectionType}
          versions={versionsQuery.data?.items ?? []}
          onRestoreVersion={(id) => restoreVersion.mutate(id)}
        />

        <div className="flex min-h-0 flex-col gap-2">
          <div className="flex items-center gap-2">
            <input
              value={draftTitle}
              onChange={(e) => setDraftTitle(e.target.value)}
              className="h-8 flex-1 rounded-md border border-border bg-background px-2.5 text-[13px] font-medium text-foreground"
              placeholder="Manuscript title"
            />
            {input ? (
              <span className="text-[11px] tabular-nums text-muted-foreground">{input.length}</span>
            ) : null}
          </div>

          {grounded.isPending ? (
            <ResearchProgressStage
              active
              liveMetric={
                grounded.jobStatus ||
                "Organising accepted EvidenceObjects for this section"
              }
            />
          ) : grounded.last?.status === "ok" ? (
            <ResearchProgressStage
              active={false}
              doneLabel={
                (grounded.last.section_type || sectionType) === "literature_review"
                  ? "Literature Review Ready"
                  : `${(grounded.last.section_type || sectionType).replaceAll("_", " ")} ready`
              }
            />
          ) : null}

          <div className="flex flex-wrap items-center gap-1.5">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 gap-1 text-[11px]"
              disabled={activeId == null || currentProjectId == null || activeDoc?.status === "deleted"}
              title="Insert citation (Ctrl+Shift+C)"
              onClick={() => setCitePickerOpen(true)}
            >
              <Quote className="size-3" /> Cite
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-7 text-[11px]"
              disabled={activeId == null || activeDoc?.status === "deleted"}
              title="Remove selected [#id] marker and binding"
              onClick={() => void removeSelectedCite()}
            >
              Remove cite
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-7 text-[11px]"
              title="Jump to Evidence Inspector (uses caret [#id] or selection)"
              onClick={() => {
                const el = editorRef.current;
                if (el) {
                  const eid = selectedEvidenceMarkerId(
                    input,
                    el.selectionStart,
                    el.selectionEnd,
                  );
                  if (eid != null) {
                    setSelectedText(`[#${eid}]`);
                    setCiteHoverPreview(`Evidence #${eid} — Inspector rail`);
                  }
                }
                document
                  .getElementById("writing-evidence-rail")
                  ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
              }}
            >
              Inspect
            </Button>
            <span className="text-[10px] text-muted-foreground">Ctrl+Shift+C · [#id] = grounded</span>
          </div>

          {citePickerOpen && currentProjectId != null ? (
            <CitationInsertPicker
              open={citePickerOpen}
              projectId={currentProjectId}
              onClose={() => setCitePickerOpen(false)}
              onInsert={handleCiteInsert}
              className="mb-1"
            />
          ) : null}

          {citeHoverPreview ? (
            <p className="rounded-md border border-border bg-muted/30 px-2 py-1.5 text-[11px] text-muted-foreground">
              Preview: {citeHoverPreview}
            </p>
          ) : null}

          <div className="manuscript-surface relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-border/80 bg-[#faf9f7] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)] sm:p-5 dark:bg-[#121212]">
            <textarea
              ref={editorRef}
              value={input}
              onChange={(e) => {
                const next = e.target.value;
                setInput(next);
                if (groundedBaseline != null) {
                  setEditsSinceInsert(Math.abs(next.length - groundedBaseline.length));
                }
              }}
              onSelect={() => {
                const el = editorRef.current;
                if (!el) return;
                const start = el.selectionStart ?? 0;
                const end = el.selectionEnd ?? 0;
                if (end > start) setSelectedText(el.value.slice(start, end));
                const eid = selectedEvidenceMarkerId(input, start, end);
                if (eid != null) {
                  setCiteHoverPreview(`Evidence #${eid} — use Inspect to open the Evidence rail`);
                }
              }}
              onMouseUp={() => {
                const el = editorRef.current;
                if (!el) return;
                const start = el.selectionStart ?? 0;
                const end = el.selectionEnd ?? 0;
                if (end > start) setSelectedText(el.value.slice(start, end));
              }}
              onKeyDown={(e) => {
                if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "c") {
                  e.preventDefault();
                  setCitePickerOpen(true);
                }
              }}
              placeholder="Manuscript — write or paste your literature review. Click Write literature review to draft from evidence."
              rows={18}
              aria-label="Manuscript editor"
              disabled={activeDoc?.status === "deleted"}
              className="relative z-[1] mx-auto min-h-[24rem] w-full max-w-[42rem] flex-1 resize-y border-0 bg-transparent px-1 py-2 text-[15px] leading-[1.8] tracking-[-0.011em] text-zinc-900 outline-none placeholder:text-zinc-400 focus:ring-0 dark:text-zinc-100 dark:placeholder:text-zinc-500"
            />
          </div>

          {warning && (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-[12px] text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0" /> {warning}
            </div>
          )}

          {loading ? (
            <div
              role="status"
              aria-busy="true"
              aria-label="Applying style transform"
              className="space-y-2 rounded-lg border border-border p-3"
            >
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-3.5 w-full" />
              <Skeleton className="h-3.5 w-[92%]" />
              <Skeleton className="h-3.5 w-[78%]" />
              <Skeleton className="h-3.5 w-2/3" />
            </div>
          ) : result ? (
            <div className="rounded-lg border border-border bg-card p-2">
              <div className="mb-1 flex items-center justify-between">
                <p className="text-[11px] font-medium uppercase tracking-wide text-amber-800 dark:text-amber-200">
                  Style output · not evidence-backed
                </p>
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 gap-1 text-[11px]"
                    onClick={() => {
                      setInput(result);
                      setResult("");
                      toast.success("Moved to manuscript");
                    }}
                  >
                    <RefreshCw className="size-3" /> Use
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
              </div>
              <motion.textarea
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                value={result}
                onChange={(e) => setResult(e.target.value)}
                rows={8}
                className="w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-[13px] leading-relaxed outline-none focus:border-ring"
              />
            </div>
          ) : null}
        </div>

        <div className="flex min-h-0 flex-col gap-2 overflow-auto">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Evidence &amp; reviewer
          </p>

          {grounded.last && (
            <div
              className={cn(
                "rounded-lg border p-3 text-[12px]",
                grounded.last.status === "ok"
                  ? "border-emerald-700/30 bg-emerald-500/5"
                  : "border-amber-700/30 bg-amber-500/5",
              )}
              role="status"
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <p className="font-medium text-foreground">
                  {grounded.last.status === "ok"
                    ? "Grounded draft"
                    : "Blocked — insufficient evidence"}
                </p>
                <span className="text-[10px] uppercase text-muted-foreground">
                  {grounded.last.mode}
                </span>
              </div>
              {grounded.last.status === "blocked" ? (
                <p className="text-muted-foreground">
                  {grounded.last.blocked_reason || "insufficient_evidence"}. Extract and accept
                  evidence from Research Ready papers, then retry.
                </p>
              ) : (
                <>
                  <GroundedDraftVerify
                    writing={grounded.last}
                    onRevise={runGroundedGenerate}
                    onAcceptSection={acceptGroundedSection}
                    acceptAllowed={grounded.last.accept_allowed !== false}
                    onInspectEvidence={(binding) => {
                      const text = (binding.claim || binding.quote || "").trim();
                      if (text) setSelectedText(text.slice(0, 2000));
                      document
                        .getElementById("writing-evidence-rail")
                        ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
                    }}
                  />
                  {grounded.last.accept_allowed === false ? (
                    <p className="mt-2 text-[11px] font-medium text-amber-800 dark:text-amber-200">
                      Accept disabled — Research Reviewer found grounding errors. Revise before
                      inserting into the manuscript.
                    </p>
                  ) : null}
                  <ResearchReviewerPanel
                    className="mt-2"
                    documentId={activeId}
                    liveReview={grounded.last.review}
                    refreshKey={reviewerRefresh}
                    onFocusSection={(sectionId) => {
                      document
                        .getElementById(`writing-section-${sectionId}`)
                        ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
                    }}
                  />
                  {grounded.last.warnings?.length ? (
                    <p className="mt-2 text-[11px] text-amber-800 dark:text-amber-200">
                      {grounded.last.warnings.join(" ")}
                    </p>
                  ) : null}
                  <p className="mt-2 text-[10px] text-muted-foreground">{grounded.last.disclaimer}</p>
                  {editsSinceInsert > 0 ? (
                    <p className="mt-1 text-[10px] text-muted-foreground">
                      Char edits since insert: {editsSinceInsert}
                    </p>
                  ) : null}
                  <div className="mt-2 flex gap-1">
                    <Button
                      size="sm"
                      className="h-7 text-[11px]"
                      disabled={grounded.last.accept_allowed === false}
                      onClick={() => void acceptGroundedIntoManuscript()}
                    >
                      Accept into manuscript
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 text-[11px]"
                      onClick={() => {
                        if (groundedBaseline != null) {
                          trackWritingEvent("edits_before_export", {
                            section_type: sectionType,
                            edits_since_insert: editsSinceInsert,
                            char_delta: Math.abs(input.length - groundedBaseline.length),
                          });
                        }
                        grounded.clear();
                        setGroundedBaseline(null);
                        setEditsSinceInsert(0);
                      }}
                    >
                      Dismiss
                    </Button>
                  </div>
                </>
              )}
            </div>
          )}

          <div id="writing-evidence-rail" className="min-h-0">
            <EvidenceInspectorPanel
              result={evidenceExplain.result}
              status={evidenceExplain.status}
              stickyText={selectedText}
              documentId={activeId}
              projectId={currentProjectId}
              onBound={() => setEvidenceRefresh((n) => n + 1)}
            />
          </div>
          {activeId != null && !grounded.last ? (
            <ResearchReviewerPanel
              className="mt-2"
              documentId={activeId}
              refreshKey={reviewerRefresh}
              onFocusSection={(sectionId) => {
                document
                  .getElementById(`writing-section-${sectionId}`)
                  ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
              }}
            />
          ) : null}
          </div>
        </div>
        </>
      )}

      <ConfirmDialog
        open={confirmDeleteDoc}
        onOpenChange={setConfirmDeleteDoc}
        title="Delete this draft?"
        entityName={draftTitle || "Untitled draft"}
        description="The manuscript moves to Deleted. You can still view it there as read-only."
        consequence="Export snapshots for this draft remain until you clear browser session data."
        confirmLabel="Delete draft"
        cancelLabel="Keep draft"
        destructive
        onConfirm={async () => {
          if (activeDoc == null) return;
          await updateStatus.mutateAsync({ id: activeDoc.id, status: "deleted" });
        }}
      />
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
  const docsQuery = useQuery({
    queryKey: ["writing", "documents", currentProjectId ?? "all", "export"],
    queryFn: () =>
      writingApi.listDocuments(currentProjectId as number, {
        includeArchived: false,
        includeDeleted: false,
      }),
    enabled: currentProjectId != null,
  });
  const writingDocs = docsQuery.data?.items ?? [];

  function download(url: string, fname: string) {
    const a = document.createElement("a");
    a.href = url;
    a.download = fname;
    a.click();
  }

  async function exportLitReviewDoc(doc: { id: number; title?: string; content?: string }) {
    const snap = loadGroundedExportSnapshot(doc.id);
    const body = (doc.content || snap?.body || "").trim();
    if (!body) {
      toast.error("Draft is empty — generate and insert a grounded review first");
      return;
    }
    if (!snap?.writing) {
      toast.error("No evidence snapshot — regenerate and Accept a grounded review first");
      return;
    }
    const wantBib = loadResearchPrefs().exportBundle === "md_bib";
    try {
      const res = await writingApi.exportLitReview(doc.id, {
        writing: snap.writing,
        writing_version: snap.writing_version,
        title: doc.title || snap.title || "Literature review",
        body,
        format: wantBib ? "markdown_bibtex" : "markdown",
      });
      const base = res.filename_base || `literature-review-${doc.id}`;
      downloadMarkdownFile(`${base}.md`, res.markdown);
      const wroteBib = Boolean(res.bibtex?.trim());
      if (wroteBib && res.bibtex) {
        downloadTextFile(`${base}.bib`, res.bibtex, "application/x-bibtex;charset=utf-8");
      }
      trackWritingEvent("grounded_export", {
        document_id: doc.id,
        has_evidence_appendix: true,
        has_bibtex: wroteBib,
      });
      trackWorkflowEvent("export_completed", {
        projectId: currentProjectId,
        meta: {
          document_id: doc.id,
          has_bibtex: wroteBib,
          format: wroteBib ? "markdown_bibtex" : "markdown",
          server_gated: true,
        },
      });
      toast.success(
        wroteBib
          ? "Exported Markdown + BibTeX (evidence → paper → citation)"
          : wantBib
            ? "Exported Markdown with appendix (no BibTeX metadata yet)"
            : "Exported Markdown",
      );
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "message" in err
          ? String((err as { message: string }).message)
          : "Export failed";
      toast.error(msg === "session_expired" ? "Session expired" : msg);
    }
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
    disabled,
    disabledReason,
  }: {
    title: string;
    subtitle?: string;
    formats: { label: string; fmt: string }[];
    onExport: (fmt: string) => void;
    disabled?: boolean;
    disabledReason?: string;
  }) {
    return (
      <div className="border-b border-border py-2 last:border-0">
        <div className="flex items-center justify-between gap-3">
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
                disabled={disabled}
                title={disabled ? disabledReason : undefined}
                onClick={() => onExport(fmt)}
              >
                <Download className="size-3" /> {label}
              </Button>
            ))}
          </div>
        </div>
        {disabled && disabledReason ? (
          <p className="mt-1.5 text-[11px] text-amber-800 dark:text-amber-200">{disabledReason}</p>
        ) : null}
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
          <FileText className="size-3.5 text-muted-foreground" />
          <h2 className="text-[12px] font-semibold">Evidence-backed literature review</h2>
        </div>
        {writingDocs.length === 0 ? (
          <p className="py-3 text-[12px] text-muted-foreground">
            No writing drafts yet. Generate from evidence on the Draft tab, then export here.
          </p>
        ) : (
          writingDocs.map((doc) => {
            const snap = loadGroundedExportSnapshot(doc.id);
            const gate = canExportGroundedLitReview(snap?.writing);
            const blocked = !snap?.writing || !gate.ok;
            const reason = !snap?.writing
              ? "Generate and Accept a grounded review on the Draft tab first"
              : gate.reason;
            return (
              <ExportRow
                key={doc.id}
                title={doc.title || "Untitled draft"}
                subtitle={
                  snap?.writing
                    ? `Markdown + BibTeX · evidence → paper → citation`
                    : "Markdown · generate from evidence to attach appendix"
                }
                formats={[
                  {
                    label: loadResearchPrefs().exportBundle === "md_bib" ? ".md + .bib" : ".md",
                    fmt: "md",
                  },
                ]}
                disabled={blocked}
                disabledReason={reason}
                onExport={() => void exportLitReviewDoc(doc)}
              />
            );
          })
        )}
      </section>

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

/** Writing desk — Outline | Manuscript | Evidence (UI_UX_VISION_BETA_v1.0). */
export function WritingPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const [tab, setTab] = useState<Tab>(tabParam === "export" ? "export" : "draft");

  useEffect(() => {
    const action = searchParams.get("action");
    const focus = searchParams.get("focus");
    if (action === "lit-review" || focus === "evidence") {
      setTab("draft");
      return;
    }
    if (tabParam === "export" || tabParam === "draft") setTab(tabParam);
  }, [tabParam, searchParams]);

  function selectTab(key: Tab) {
    setTab(key);
    const next = new URLSearchParams(searchParams);
    if (key === "draft") next.delete("tab");
    else next.set("tab", key);
    setSearchParams(next, { replace: true });
  }

  return (
    <PageContainer
      title="Writing"
      description="Literature review desk — outline, manuscript, and evidence."
      dense
    >
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
            onClick={() => selectTab(key)}
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
