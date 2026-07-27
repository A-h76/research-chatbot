import { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import {
  BookOpen, Calendar,
  ChevronLeft, BookMarked, ExternalLink,
  MessageSquare, ArrowRight,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ObjectHeader } from "@/components/layout/ObjectHeader";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/apiClient";
import { isTypingTarget } from "@/lib/keyboard";
import { useFile, usePaperAnalysis, usePatchFile, useAnalyzeDocument } from "@/features/files/useFiles";
import { useCitationFromPaper } from "@/features/citations/useCitations";
import { useCreateConversation } from "@/features/chat/hooks/useConversation";
import type { MetadataInputValue } from "@/features/analysis/components/MetadataInput";
import { analysisToMarkdown } from "@/features/analysis/toAnalysisMarkdown";
import { toast } from "@/components/common/Toast";
import type { ReadingStatus } from "@/types/api";
import { PipelineDevPanel, usePipeline, AiStateBadge, PipelineStatusPanel, isPipelineProcessing } from "@/features/pipeline";
import { parsePaperTab, type PaperTabId } from "../tabs";
import { PaperWorkspaceTabList, PaperTabPanel } from "../components/PaperWorkspaceTabs";
import { PaperOverviewTab } from "../components/PaperOverviewTab";
import { PaperNarrativeTab } from "../components/PaperNarrativeTab";
import { PaperStructureTab } from "../components/PaperStructureTab";
import { PaperClassificationTab } from "../components/PaperClassificationTab";
import { PaperEntitiesTab } from "../components/PaperEntitiesTab";
import { PaperEvidenceTab } from "../components/PaperEvidenceTab";
import { PaperKnowledgeGraphTab } from "../components/PaperKnowledgeGraphTab";
import { PaperRelatedTab } from "../components/PaperRelatedTab";

const ANALYZE_ERROR_MESSAGES: Record<string, string> = {
  not_ready: "This paper is still being processed. Try again in a moment.",
  token_quota_exceeded: "Monthly AI usage quota exceeded.",
  invalid_domain: "That domain isn't recognized.",
  no_text: "No readable text could be extracted from this document.",
  storage_unavailable: "Could not read the document from storage.",
  not_found: "Document not found.",
};

function analyzeErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    return ANALYZE_ERROR_MESSAGES[err.message] ?? "Analysis failed. Please try again.";
  }
  return "Analysis failed. Please try again.";
}

function SkeletonSection() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
    </div>
  );
}

const STATUS_CONFIG: Record<ReadingStatus, { label: string; color: string; next: ReadingStatus }> = {
  unread:  { label: "Unread",  color: "bg-muted text-muted-foreground border-border", next: "reading" },
  reading: { label: "Reading", color: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800", next: "read" },
  read:    { label: "Read ✓",  color: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800", next: "unread" },
};

function ReadingStatusBadge({
  status,
  onChange,
}: {
  status: ReadingStatus;
  onChange: (s: ReadingStatus) => void;
}) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.unread;
  return (
    <button
      onClick={() => onChange(cfg.next)}
      title="Click to cycle reading status"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors hover:opacity-80",
        cfg.color,
      )}
    >
      <BookMarked className="size-3" />
      {cfg.label}
    </button>
  );
}

/**
 * Paper Workspace shell (M4).
 * Routing: `/papers/:id` · `/papers/:id?tab=overview|narrative|…`
 * Chat tab opens the existing PaperChatPage (no redesign).
 */
export function PaperOverviewPage() {
  const { fileId } = useParams<{ fileId: string }>();
  const navigate = useNavigate();
  const id = fileId ? Number(fileId) : null;

  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = parsePaperTab(searchParams.get("tab"));
  const focusRef = searchParams.get("ref");

  const [domain, setDomain] = useState<string | null>(searchParams.get("domain"));
  const [metadata, setMetadata] = useState<MetadataInputValue>({
    title: searchParams.get("title") ?? "",
    authors: searchParams.get("authors") ?? "",
    venue: searchParams.get("venue") ?? "",
    year: searchParams.get("year") ?? "",
  });
  const [userQuery, setUserQuery] = useState(searchParams.get("query") ?? "");

  // Preserve `tab` while syncing narrative form params into the URL.
  useEffect(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        const setOrDel = (key: string, value: string | null | undefined) => {
          if (value) next.set(key, value);
          else next.delete(key);
        };
        setOrDel("domain", domain);
        setOrDel("title", metadata.title);
        setOrDel("authors", metadata.authors);
        setOrDel("venue", metadata.venue);
        setOrDel("year", metadata.year);
        setOrDel("query", userQuery.trim() || null);
        // Keep tab as-is (including absent = overview)
        return next;
      },
      { replace: true },
    );
  }, [domain, metadata, userQuery, setSearchParams]);

  // Deep link ?tab=chat → existing chat route
  useEffect(() => {
    if (activeTab === "chat" && id != null) {
      navigate(`/papers/${id}/chat`, { replace: true });
    }
  }, [activeTab, id, navigate]);

  // D9 — Paper workspace shortcuts (Interaction Guidelines §5); ignore while typing
  useEffect(() => {
    if (id == null) return;
    const TAB_BY_DIGIT: Record<string, PaperTabId> = {
      "1": "overview",
      "2": "structure",
      "3": "classification",
      "4": "entities",
      "5": "evidence",
      "6": "graph",
      "7": "narrative",
      "8": "chat",
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (isTypingTarget(e.target)) return;
      const key = e.key.toLowerCase();
      if (TAB_BY_DIGIT[key]) {
        e.preventDefault();
        selectTab(TAB_BY_DIGIT[key]!);
        return;
      }
      if (key === "c") {
        e.preventDefault();
        selectTab("chat");
        return;
      }
      if (key === "e") {
        e.preventDefault();
        selectTab("evidence");
        return;
      }
      if (key === "s") {
        e.preventDefault();
        selectTab("structure");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // selectTab closes over searchParams setters — rebind when id changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const { data: file, isLoading: fileLoading } = useFile(id);
  const { data: analysis, isLoading: analysisLoading } = usePaperAnalysis(id);
  const { derived: pipelineDerived } = usePipeline(id, {
    fileContentHash: null,
  });
  const patchFile = usePatchFile();
  const citationFromPaper = useCitationFromPaper();
  const analyzeDocument = useAnalyzeDocument();
  const createConversation = useCreateConversation();

  const displayTitle = file?.title || file?.name || "Paper";
  const analysisDone = analysis?.status === "done";
  const generating =
    analysis?.status === "pending" ||
    analysis?.status === "running" ||
    analyzeDocument.isPending;
  const stillProcessing = file?.meta_status === "pending" || file?.meta_status === "running";
  const notReadyError =
    analyzeDocument.error instanceof ApiError && analyzeDocument.error.message === "not_ready";

  function selectTab(tab: PaperTabId) {
    if (tab === "chat" && id != null) {
      navigate(`/papers/${id}/chat`);
      return;
    }
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (tab === "overview") next.delete("tab");
        else next.set("tab", tab);
        return next;
      },
      { replace: false },
    );
  }

  function handleStatusChange(s: ReadingStatus) {
    if (!id) return;
    patchFile.mutate(
      { id, body: { reading_status: s } },
      { onSuccess: () => toast.success(`Marked as ${s}`) },
    );
  }

  function handleChatWithPaper() {
    if (!id) return;
    navigate(`/papers/${id}/chat`);
  }

  function handleAnalyze() {
    if (id == null) return;
    analyzeDocument.mutate(
      { id, domain, metadata, user_query: userQuery.trim() || undefined },
      {
        onSuccess: () => toast.success("Analysis complete"),
        onError: (err) => toast.error(analyzeErrorMessage(err)),
      },
    );
  }

  if (fileLoading) {
    return (
      <div className="scrollbar-thin h-full overflow-y-auto">
        <div className="mx-auto max-w-3xl px-6 py-10 space-y-8">
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-4 w-1/3" />
          <div className="grid grid-cols-2 gap-4 pt-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonSection key={i} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!file || id == null) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Paper not found.
      </div>
    );
  }

  const d = analysis?.data ?? {};

  // While redirecting to chat, avoid flashing a placeholder
  if (activeTab === "chat") {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Opening chat…
      </div>
    );
  }

  return (
    <div className="scrollbar-thin h-full overflow-y-auto bg-background">
      <div className="mx-auto max-w-5xl px-5 py-5 sm:px-8 space-y-4">
        <button
          type="button"
          onClick={() => navigate("/library")}
          className="flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronLeft className="size-4" /> Library
        </button>

        <ObjectHeader
          title={displayTitle}
          meta={
            file.authors ? (
              <span className="line-clamp-2">{file.authors}</span>
            ) : undefined
          }
          status={
            <>
              <AiStateBadge derived={pipelineDerived} metaStatus={file.meta_status} />
              <ReadingStatusBadge
                status={(file.reading_status as ReadingStatus) ?? "unread"}
                onChange={handleStatusChange}
              />
              {file.year && (
                <span className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-0.5 text-[12px] text-muted-foreground">
                  <Calendar className="size-3" /> {file.year}
                </span>
              )}
              {file.venue && (
                <span className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-0.5 text-[12px] text-muted-foreground">
                  <BookOpen className="size-3" />
                  <span className="max-w-[22ch] truncate">{file.venue}</span>
                </span>
              )}
              {file.doi && (
                <a
                  href={`https://doi.org/${file.doi}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-0.5 text-[12px] text-primary hover:underline"
                >
                  DOI <ExternalLink className="size-3" />
                </a>
              )}
            </>
          }
        />

        {/* D3: processing → expanded above tabs; ready → collapsed below stage */}
        {(isPipelineProcessing(pipelineDerived, file.meta_status) ||
          pipelineDerived.isError) && (
          <PipelineStatusPanel
            derived={pipelineDerived}
            metaStatus={file.meta_status}
            updatedAt={analysis?.updated_at ?? file.created_at}
          />
        )}

        {/* Sticky tabs — primary product navigation */}
        <div className="sticky top-0 z-10 -mx-1 bg-background/95 px-1 backdrop-blur supports-[backdrop-filter]:bg-background/80">
          <PaperWorkspaceTabList active={activeTab} onSelect={selectTab} />
        </div>

        {/* Active tab content */}
        <div className="min-h-[12rem]">
          <PaperTabPanel tab="overview" active={activeTab}>
            <PaperOverviewTab
              file={file}
              fileId={id}
              onChat={handleChatWithPaper}
              chatPending={createConversation.isPending}
              citePending={citationFromPaper.isPending}
              onJumpTab={selectTab}
              onCite={async () => {
                const r = await citationFromPaper.mutateAsync({
                  fileId: id,
                  projectId: file.project_id,
                });
                if (r.existing) toast.success("Already in your citations.");
                else toast.success("Saved to citations.");
              }}
            />
          </PaperTabPanel>

          <PaperTabPanel tab="narrative" active={activeTab}>
            <PaperNarrativeTab
              file={file}
              analysis={analysis}
              analysisLoading={analysisLoading}
              analysisDone={analysisDone}
              generating={generating}
              stillProcessing={stillProcessing}
              notReadyError={notReadyError}
              domain={domain}
              onDomainChange={setDomain}
              detectedDomain={analyzeDocument.data?.domain_detected}
              userQuery={userQuery}
              onUserQueryChange={setUserQuery}
              metadata={metadata}
              onMetadataChange={(patch) => setMetadata((prev) => ({ ...prev, ...patch }))}
              onAnalyze={handleAnalyze}
              analyzeError={analyzeDocument.isError}
              analyzeErrorMessage={analyzeErrorMessage(analyzeDocument.error)}
              markdown={analysisToMarkdown(d)}
            />
          </PaperTabPanel>

          <PaperTabPanel tab="structure" active={activeTab}>
            <PaperStructureTab fileId={id} metaStatus={file.meta_status} focusRef={focusRef} />
          </PaperTabPanel>

          <PaperTabPanel tab="classification" active={activeTab}>
            <PaperClassificationTab fileId={id} metaStatus={file.meta_status} focusRef={focusRef} />
          </PaperTabPanel>

          <PaperTabPanel tab="entities" active={activeTab}>
            <PaperEntitiesTab fileId={id} metaStatus={file.meta_status} focusRef={focusRef} />
          </PaperTabPanel>

          <PaperTabPanel tab="evidence" active={activeTab}>
            <PaperEvidenceTab fileId={id} metaStatus={file.meta_status} focusRef={focusRef} />
          </PaperTabPanel>

          <PaperTabPanel tab="graph" active={activeTab}>
            <PaperKnowledgeGraphTab fileId={id} metaStatus={file.meta_status} focusRef={focusRef} />
          </PaperTabPanel>

          <PaperTabPanel tab="related" active={activeTab}>
            <PaperRelatedTab fileId={id} />
          </PaperTabPanel>

          <PaperTabPanel tab="chat" active={activeTab}>
            <div className="rounded-lg border border-border bg-muted/20 p-6 text-center space-y-3">
              <p className="text-sm text-muted-foreground">Paper chat opens in the dedicated chat view.</p>
              <Button onClick={handleChatWithPaper} className="gap-2">
                <MessageSquare className="size-4" />
                Open chat <ArrowRight className="size-3.5" />
              </Button>
            </div>
          </PaperTabPanel>
        </div>

        {/* Collapsed pipeline after Ready — details on demand */}
        {!isPipelineProcessing(pipelineDerived, file.meta_status) &&
          !pipelineDerived.isError &&
          pipelineDerived.isReady && (
            <PipelineStatusPanel
              derived={pipelineDerived}
              metaStatus={file.meta_status}
              updatedAt={analysis?.updated_at ?? file.created_at}
            />
          )}

        {import.meta.env.DEV && import.meta.env.MODE !== "production" && (
          <PipelineDevPanel fileId={id} />
        )}
        <div className="h-8" />
      </div>
    </div>
  );
}
