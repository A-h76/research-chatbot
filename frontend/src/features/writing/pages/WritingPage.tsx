import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Download, RefreshCw,
  BookOpen, FileText, MessageSquare, StickyNote,
  Quote, Plus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { WritingDeskSkeleton } from "@/components/common/ResearchSkeletons";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { useFiles } from "@/features/files/useFiles";
import { useNotes } from "@/features/notes/useNotes";
import { useConversations } from "@/features/chat/hooks/useConversation";
import { useUI } from "@/context/UIContext";
import { writingApi } from "../api";
import { toast } from "@/components/common/Toast";
import { cn } from "@/lib/utils";
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
import {
  applyBulletList,
  applyHeadingToLine,
  applyLink,
  applyNumberedList,
  applyTextColor,
  detectHeadingLevel,
  toggleInlineMark,
  type HeadingLevel,
} from "@/features/writing/utils/writingFormatHelpers";
import { ResearchProgressStage } from "@/features/writing/components/ResearchProgressStage";
import { WritingStudioTabs, type WritingStudioTabId } from "@/features/writing/components/WritingStudioTabs";
import { WritingStudioFooter } from "@/features/writing/components/WritingStudioFooter";
import { WritingManuscriptEditor } from "@/features/writing/components/WritingManuscriptEditor";
import { WritingManuscriptToolbar } from "@/features/writing/components/WritingManuscriptToolbar";
import { WritingNotesTab } from "@/features/writing/components/WritingNotesTab";
import { WritingOutlineTab } from "@/features/writing/components/WritingOutlineTab";
import { ResearchIntelligencePanel, type ReviewerPanelMode } from "@/features/writing/components/ResearchIntelligencePanel";
import {
  downloadMarkdownFile,
  downloadTextFile,
  loadGroundedExportSnapshot,
  saveGroundedExportSnapshot,
  canExportGroundedLitReview,
} from "@/features/writing/utils/groundedMarkdownExport";

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

function DraftTab({
  studioTab,
  studioTabs,
}: {
  studioTab: WritingStudioTabId;
  /** Rendered at the same baseline as the assistant panel (orange line). */
  studioTabs?: ReactNode;
}) {
  const { currentProjectId } = useUI();
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [input, setInput] = useState("");
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
  const [, setEditsSinceInsert] = useState(0);
  const [confirmDeleteDoc, setConfirmDeleteDoc] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(true);
  const [selectedCiteId, setSelectedCiteId] = useState<number | null>(null);
  const [headingLevel, setHeadingLevel] = useState<HeadingLevel>("p");
  const [textColor, setTextColor] = useState("#0f6e6a");
  const editorRef = useRef<HTMLTextAreaElement | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const handledActionRef = useRef<string | null>(null);
  const forcedReviewMode = searchParams.get("focus") === "review";

  function exitReviewFocus() {
    if (searchParams.get("focus") !== "review") return;
    const next = new URLSearchParams(searchParams);
    next.delete("focus");
    setSearchParams(next, { replace: true });
  }

  function enterReviewFocus() {
    const next = new URLSearchParams(searchParams);
    next.set("focus", "review");
    setSearchParams(next, { replace: true });
  }

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
    setEvidenceOpen(true);
    // Only when a new grounded result arrives — not on every manuscript keystroke.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional: grounded.last identity
  }, [grounded.last, activeId]);

  useEffect(() => {
    if (grounded.last) setEvidenceOpen(true);
  }, [grounded.last]);

  useEffect(() => {
    if (grounded.isPending) setEvidenceOpen(true);
  }, [grounded.isPending]);

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

  function applyFormat(
    fn: (
      content: string,
      start: number,
      end: number,
    ) => { content: string; selectionStart: number; selectionEnd: number },
  ) {
    const el = editorRef.current;
    if (!el || activeDoc?.status === "deleted") return;
    const start = el.selectionStart ?? 0;
    const end = el.selectionEnd ?? 0;
    const next = fn(input, start, end);
    setInput(next.content);
    window.requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(next.selectionStart, next.selectionEnd);
      setHeadingLevel(detectHeadingLevel(next.content, next.selectionStart));
    });
  }

  function runGroundedGenerate(nextSection?: WritingSectionType) {
    if (activeId == null || currentProjectId == null) {
      toast.error("Select a project document first");
      return;
    }
    const st = nextSection ?? sectionType;
    if (nextSection) setSectionType(nextSection);
    const focus =
      selectedText.trim() ||
      input.trim() ||
      draftTitle.trim() ||
      (st === "introduction"
        ? "Write a grounded introduction from accepted project evidence"
        : "Write a grounded literature review from accepted project evidence");
    grounded.generate({
      projectId: currentProjectId,
      documentId: activeId,
      selectedText: selectedText.trim() ? selectedText : "",
      draftFallback: focus,
      sectionType: st,
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

  /** ⌘K / journey deep-links: ?action=lit-review · ?focus=evidence|review */
  useEffect(() => {
    const action = searchParams.get("action");
    const focusTarget = searchParams.get("focus");

    if (focusTarget === "evidence" || focusTarget === "review") {
      setEvidenceOpen(true);
      if (focusTarget === "review") {
        setSelectedCiteId(null);
      } else {
        const next = new URLSearchParams(searchParams);
        next.delete("focus");
        setSearchParams(next, { replace: true });
      }
      window.requestAnimationFrame(() => {
        document
          .querySelector("[data-testid='research-reviewer-panel']")
          ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
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

    setSectionType("literature_review");
    grounded.generate({
      projectId: currentProjectId,
      documentId: activeId,
      selectedText,
      draftFallback:
        selectedText.trim() ||
        input.trim() ||
        draftTitle.trim() ||
        "Write a grounded literature review from accepted project evidence",
      sectionType: "literature_review",
    });
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
    <div className="flex min-h-0 flex-1 flex-col" data-density="low">
      {studioTab === "notes" ? (
        <WritingNotesTab projectId={currentProjectId} />
      ) : null}
      {studioTab === "outline" ? (
        <WritingOutlineTab
          sectionType={sectionType}
          onSectionTypeChange={setSectionType}
          versions={versionsQuery.data?.items ?? []}
          onRestoreVersion={(id) => restoreVersion.mutate(id)}
        />
      ) : null}
      {studioTab === "manuscript" ? (
        <div className="flex min-h-0 flex-1 overflow-hidden">
          <div className="flex min-h-0 min-w-0 flex-1 flex-col">
            {studioTabs}
            <div className="flex min-h-0 flex-1 flex-col gap-0 px-3 pb-1 pt-1">
      {currentProjectId == null && (
        <div className="shrink-0 rounded-md border border-border bg-card p-3 text-[12px] text-muted-foreground">
          Select a project to open the writing desk. Documents are always project-scoped.
        </div>
      )}
      {currentProjectId != null && docsQuery.isLoading ? (
        <WritingDeskSkeleton className="min-h-0 flex-1" />
      ) : (
        <>
          {isOffline && (
            <div
              role="status"
              aria-live="polite"
              className="shrink-0 rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-[12px] text-blue-900 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200"
            >
              You are offline. Changes stay local until the connection returns.
            </div>
          )}

          {saveState === "conflict" && (
            <div
              role="alert"
              className="flex shrink-0 flex-wrap items-center justify-between gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-[12px] text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
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

          {/* Slim action strip — manuscript is the hero */}
          <div className="flex shrink-0 flex-wrap items-center gap-1.5 px-0 pb-1.5">
            <select
              aria-label="Select writing document"
              className="h-7 max-w-[11rem] rounded-md border-0 bg-transparent px-1 text-[12px] font-medium text-foreground outline-none hover:bg-muted/50"
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
              variant="ghost"
              className="h-7 px-2 text-[11px] text-muted-foreground"
              onClick={() => createDoc.mutate()}
              disabled={createDoc.isPending || currentProjectId == null}
            >
              <Plus className="size-3.5" /> New
            </Button>

            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-7 gap-1 px-2 text-[11px] text-muted-foreground"
              disabled={
                activeId == null || currentProjectId == null || activeDoc?.status === "deleted"
              }
              title="Insert citation (Ctrl+Shift+C)"
              onClick={() => setCitePickerOpen(true)}
            >
              <Quote className="size-3" /> Cite
            </Button>

            <details className="relative ml-auto">
              <summary className="cursor-pointer list-none rounded-md px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted/50 hover:text-foreground [&::-webkit-details-marker]:hidden">
                More
              </summary>
              <div className="absolute right-0 z-20 mt-1 min-w-[10rem] rounded-lg border border-border bg-popover p-1 shadow-md">
                <div className="mb-1 flex gap-0.5 px-1 py-0.5">
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
                        "rounded px-1.5 py-0.5 text-[10px]",
                        lifecycleView === it.key
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-muted",
                      )}
                    >
                      {it.label}
                    </button>
                  ))}
                </div>
                {activeDoc?.status === "active" && (
                  <button
                    type="button"
                    className="block w-full rounded-md px-2 py-1.5 text-left text-[12px] hover:bg-muted"
                    onClick={() => updateStatus.mutate({ id: activeDoc.id, status: "archived" })}
                  >
                    Archive draft
                  </button>
                )}
                {activeDoc?.status === "archived" && (
                  <>
                    <button
                      type="button"
                      className="block w-full rounded-md px-2 py-1.5 text-left text-[12px] hover:bg-muted"
                      onClick={() => updateStatus.mutate({ id: activeDoc.id, status: "active" })}
                    >
                      Restore
                    </button>
                    <button
                      type="button"
                      className="block w-full rounded-md px-2 py-1.5 text-left text-[12px] hover:bg-muted"
                      onClick={() => setConfirmDeleteDoc(true)}
                    >
                      Delete
                    </button>
                  </>
                )}
                <button
                  type="button"
                  className="block w-full rounded-md px-2 py-1.5 text-left text-[12px] hover:bg-muted"
                  disabled={activeId == null || activeDoc?.status === "deleted"}
                  onClick={() => void removeSelectedCite()}
                >
                  Remove cite
                </button>
                <button
                  type="button"
                  className="block w-full rounded-md px-2 py-1.5 text-left text-[12px] hover:bg-muted"
                  onClick={() => {
                    enterReviewFocus();
                    setEvidenceOpen(true);
                  }}
                >
                  Open review
                </button>
                <button
                  type="button"
                  className="block w-full rounded-md px-2 py-1.5 text-left text-[12px] hover:bg-muted"
                  onClick={() => setEvidenceOpen((v) => !v)}
                >
                  {evidenceOpen ? "Hide assistant" : "Show assistant"}
                </button>
              </div>
            </details>
          </div>

          {/* Manuscript column */}
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <div className="px-3 pt-2 sm:px-8">
                <input
                  value={draftTitle}
                  onChange={(e) => setDraftTitle(e.target.value)}
                  className="w-full border-0 bg-transparent text-[1.35rem] font-semibold tracking-tight text-foreground outline-none placeholder:text-muted-foreground/50"
                  placeholder="Untitled draft"
                />
              </div>

              <WritingManuscriptToolbar
                heading={headingLevel}
                textColor={textColor}
                disabled={activeDoc?.status === "deleted"}
                onHeading={(level) => {
                  setHeadingLevel(level);
                  applyFormat((c, s, e) => applyHeadingToLine(c, s, e, level));
                }}
                onBold={() => applyFormat((c, s, e) => toggleInlineMark(c, s, e, "**"))}
                onItalic={() => applyFormat((c, s, e) => toggleInlineMark(c, s, e, "*"))}
                onBullet={() => applyFormat(applyBulletList)}
                onNumbered={() => applyFormat(applyNumberedList)}
                onLink={() => applyFormat(applyLink)}
                onColor={(color) => {
                  setTextColor(color);
                  applyFormat((c, s, e) => applyTextColor(c, s, e, color));
                }}
                onMore={() => setCitePickerOpen(true)}
              />

              {grounded.isPending ? (
                <ResearchProgressStage
                  active
                  liveMetric={
                    grounded.jobStatus &&
                    !/EvidenceObject|pipeline|cognitive/i.test(grounded.jobStatus)
                      ? grounded.jobStatus
                      : "Organising accepted evidence for this section"
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

              {citePickerOpen && currentProjectId != null ? (
                <CitationInsertPicker
                  open={citePickerOpen}
                  projectId={currentProjectId}
                  onClose={() => setCitePickerOpen(false)}
                  onInsert={handleCiteInsert}
                  className="mx-3 mt-2 shrink-0"
                />
              ) : null}

              {citeHoverPreview ? (
                <p className="mx-3 mt-1 shrink-0 rounded-md border border-border bg-muted/30 px-2 py-1.5 text-[11px] text-muted-foreground">
                  Preview: {citeHoverPreview}
                </p>
              ) : null}

              <div
                className="manuscript-surface relative flex min-h-0 flex-1 flex-col overflow-hidden bg-background px-3 pb-2 pt-1 sm:px-8"
                data-density="low"
              >
                <WritingManuscriptEditor
                  editorRef={editorRef}
                  value={input}
                  selectedCiteId={selectedCiteId}
                  disabled={activeDoc?.status === "deleted"}
                  onCiteSelect={(eid) => {
                    setSelectedCiteId(eid);
                    setSelectedText(`[#${eid}]`);
                    setCiteHoverPreview(`Evidence #${eid}`);
                    exitReviewFocus();
                    setEvidenceOpen(true);
                    setEvidenceRefresh((n) => n + 1);
                  }}
                  onSelectionChange={(s, e) => {
                    setHeadingLevel(detectHeadingLevel(input, s));
                    if (e > s) setSelectedText(input.slice(s, e));
                  }}
                  onChange={(next) => {
                    setInput(next);
                    if (groundedBaseline != null) {
                      setEditsSinceInsert(Math.abs(next.length - groundedBaseline.length));
                    }
                  }}
                  onKeyDown={(e) => {
                    if (
                      (e.ctrlKey || e.metaKey) &&
                      e.shiftKey &&
                      e.key.toLowerCase() === "c"
                    ) {
                      e.preventDefault();
                      setCitePickerOpen(true);
                    }
                  }}
                />
              </div>

              {grounded.last && grounded.last.status === "ok" ? (
                <div className="mx-3 mb-2 shrink-0 rounded-lg border border-border p-3 text-[12px]">
                  <GroundedDraftVerify
                    writing={grounded.last}
                    onRevise={runGroundedGenerate}
                    onAcceptSection={acceptGroundedSection}
                    acceptAllowed={grounded.last.accept_allowed !== false}
                    onInspectEvidence={(binding) => {
                      const eid = binding.evidence_id;
                      if (typeof eid === "number") {
                        setSelectedCiteId(eid);
                        setSelectedText(`[#${eid}]`);
                      } else {
                        const text = (binding.claim || binding.quote || "").trim();
                        if (text) setSelectedText(text.slice(0, 2000));
                      }
                      setEvidenceOpen(true);
                    }}
                  />
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
                        grounded.clear();
                        setGroundedBaseline(null);
                        setEditsSinceInsert(0);
                      }}
                    >
                      Dismiss
                    </Button>
                  </div>
                </div>
              ) : null}

              <WritingStudioFooter content={input} saveState={saveState} />
          </div>
        </>
      )}
          </div>
        </div>

            {evidenceOpen ? (
              <ResearchIntelligencePanel
                mode={
                  (forcedReviewMode
                    ? "review"
                    : selectedCiteId != null
                      ? "citation"
                      : selectedText.trim() && !/^\[#\d+\]$/.test(selectedText.trim())
                        ? "selection"
                        : "assist") as ReviewerPanelMode
                }
                selectedEvidenceId={selectedCiteId}
                explainResult={evidenceExplain.result}
                explainStatus={evidenceExplain.status}
                stickyText={selectedText}
                documentId={activeId}
                projectId={currentProjectId}
                onBound={() => setEvidenceRefresh((n) => n + 1)}
                reviewerRefresh={reviewerRefresh}
                groundedReview={grounded.last?.review}
                manuscript={input}
                writingBusy={grounded.isPending}
                onDraft={(section) => {
                  exitReviewFocus();
                  setEvidenceOpen(true);
                  runGroundedGenerate(section);
                }}
                onCite={() => setCitePickerOpen(true)}
                onReview={() => {
                  enterReviewFocus();
                  setEvidenceOpen(true);
                }}
                onClose={() => {
                  setEvidenceOpen(false);
                  exitReviewFocus();
                }}
              />
            ) : null}

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
      ) : null}
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

type StudioSurface = WritingStudioTabId;

/** Writing Studio — familiar three-pane research writing interaction model. */
export function WritingPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const [tab, setTab] = useState<StudioSurface>(() => {
    if (tabParam === "export") return "export";
    if (tabParam === "notes") return "notes";
    if (tabParam === "outline") return "outline";
    return "manuscript";
  });

  useEffect(() => {
    const action = searchParams.get("action");
    const focus = searchParams.get("focus");
    if (action === "lit-review" || focus === "evidence" || focus === "review") {
      setTab("manuscript");
      return;
    }
    if (tabParam === "export" || tabParam === "notes" || tabParam === "outline") {
      setTab(tabParam);
    } else if (tabParam === "draft" || !tabParam) {
      setTab("manuscript");
    }
  }, [tabParam, searchParams]);

  function selectTab(key: StudioSurface) {
    setTab(key);
    const next = new URLSearchParams(searchParams);
    if (key === "manuscript") next.delete("tab");
    else next.set("tab", key);
    setSearchParams(next, { replace: true });
  }

  const tabsEl = (
    <WritingStudioTabs
      active={tab === "export" ? "export" : tab}
      onChange={(t) => selectTab(t)}
      showExport
      onExport={() => selectTab("export")}
    />
  );

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      {tab === "manuscript" ? (
        <DraftTab studioTab={tab} studioTabs={tabsEl} />
      ) : (
        <>
          {tabsEl}
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden px-3 pb-2 pt-1">
            {tab === "export" ? (
              <div className="min-h-0 flex-1 overflow-y-auto scrollbar-thin">
                <ExportTab />
              </div>
            ) : (
              <DraftTab studioTab={tab} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
